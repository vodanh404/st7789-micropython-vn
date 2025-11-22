"""XPT2046 Touch module with Rotation support & Inverted Calibration Fix."""
from time import sleep
from micropython import const

class Touch(object):
    """Serial interface for XPT2046 Touch Screen Controller."""

    # Command constants
    GET_X = const(0b11010000)  # X position
    GET_Y = const(0b10010000)  # Y position
    GET_Z1 = const(0b10110000)  # Z1 position
    GET_Z2 = const(0b11000000)  # Z2 position
    GET_TEMP0 = const(0b10000000)  # Temperature 0
    GET_TEMP1 = const(0b11110000)  # Temperature 1
    GET_BATTERY = const(0b10100000)  # Battery monitor
    GET_AUX = const(0b11100000)  # Auxiliary input to ADC

    def __init__(self, spi, cs, int_pin=None, int_handler=None,
                 tft=None, 
                 width=240, height=320,
                 x_min=100, x_max=1962, y_min=100, y_max=1900,
                 rotation=0): 
        """Initialize touch screen controller.

        Args:
            spi: SPI object
            cs: Chip Select pin
            tft: (Optional) Đối tượng màn hình ST7789 để tự động đồng bộ
            width: Chiều rộng vật lý (nếu không dùng tft)
            height: Chiều cao vật lý (nếu không dùng tft)
            x_min, x_max: Giá trị calibration cho trục X (có thể đảo ngược để lật trục)
            y_min, y_max: Giá trị calibration cho trục Y
            rotation: Góc xoay 0-3 (nếu không dùng tft)
        """
        self.spi = spi
        self.cs = cs
        self.cs.init(self.cs.OUT, value=1)
        self.rx_buf = bytearray(3)
        self.tx_buf = bytearray(3)

        # --- TỰ ĐỘNG CẤU HÌNH TỪ TFT NẾU CÓ ---
        if tft is not None:
            # Lấy kích thước vật lý gốc (thường là Portrait)
            if hasattr(tft, 'physical_width'):
                self.width = tft.physical_width
                self.height = tft.physical_height
            else:
                self.width = width
                self.height = height
            
            # Lấy góc xoay hiện tại của màn hình
            self.rotation = tft._rotation
        else:
            self.width = width
            self.height = height
            self.rotation = rotation 

        # --- CALIBRATION ---
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        
        # Tính toán hệ số (Multiplier)
        # Nếu x_min > x_max (đảo trục), multiplier sẽ ra số âm -> Tự động lật
        self.x_multiplier = self.width / (x_max - x_min)
        self.x_add = x_min * -self.x_multiplier
        
        self.y_multiplier = self.height / (y_max - y_min)
        self.y_add = y_min * -self.y_multiplier

        if int_pin is not None:
            self.int_pin = int_pin
            self.int_pin.init(int_pin.IN)
            self.int_handler = int_handler
            self.int_locked = False
            int_pin.irq(trigger=int_pin.IRQ_FALLING | int_pin.IRQ_RISING,
                        handler=self.int_press)

    def _rotate_coords(self, x, y):
        """Áp dụng logic xoay cho tọa độ đã chuẩn hóa."""
        W, H = self.width, self.height
        
        if self.rotation == 1: # 90 độ (Landscape)
            x_new = y
            y_new = W - 1 - x
            return x_new, y_new
        
        elif self.rotation == 2: # 180 độ (Inv Portrait)
            x_new = W - 1 - x
            y_new = H - 1 - y
            return x_new, y_new
            
        elif self.rotation == 3: # 270 độ (Inv Landscape)
            x_new = H - 1 - y
            y_new = x
            return x_new, y_new
            
        else: # 0 độ (Portrait)
            return x, y

    def get_touch(self):
        """Đọc tọa độ chạm với khử nhiễu (sampling)."""
        timeout = 2
        confidence = 5
        buff = [[0, 0] for x in range(confidence)]
        buf_length = confidence 
        buffptr = 0 
        nsamples = 0 
        while timeout > 0:
            if nsamples == buf_length:
                meanx = sum([c[0] for c in buff]) // buf_length
                meany = sum([c[1] for c in buff]) // buf_length
                
                dev = sum([(c[0] - meanx)**2 + (c[1] - meany)**2 for c in buff]) / buf_length
                
                if dev <= 50: 
                    x_norm, y_norm = self.normalize(meanx, meany)
                    return self._rotate_coords(x_norm, y_norm)

            sample = self.raw_touch() 
            if sample is None:
                nsamples = 0    
            else:
                buff[buffptr] = sample 
                buffptr = (buffptr + 1) % buf_length 
                nsamples = min(nsamples + 1, buf_length) 

            sleep(.05)
            timeout -= .05
        return None

    def normalize(self, x, y):
        """Chuyển đổi từ giá trị thô (raw) sang tọa độ màn hình (pixel)."""
        x = int(self.x_multiplier * x + self.x_add)
        y = int(self.y_multiplier * y + self.y_add)
        return x, y

    def raw_touch(self):
        """Đọc giá trị thô X, Y từ cảm biến."""
        x = self.send_command(self.GET_X)
        y = self.send_command(self.GET_Y)
        
        # --- FIX QUAN TRỌNG ---
        # Sử dụng min/max linh hoạt để hỗ trợ trường hợp đảo trục (min > max)
        x_valid = min(self.x_min, self.x_max) <= x <= max(self.x_min, self.x_max)
        y_valid = min(self.y_min, self.y_max) <= y <= max(self.y_min, self.y_max)
        
        if x_valid and y_valid:
            return (x, y)
        else:
            return None

    def send_command(self, command):
        """Gửi lệnh SPI tới XPT2046."""
        self.tx_buf[0] = command
        self.cs(0)
        self.spi.write_readinto(self.tx_buf, self.rx_buf)
        self.cs(1)
        return (self.rx_buf[1] << 4) | (self.rx_buf[2] >> 4)