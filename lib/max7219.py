"""
MicroPython max7219 cascadable 8x8 LED matrix driver
https://github.com/mcauser/micropython-max7219
MIT License
Copyright (c) 2017 Mike Causer
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from micropython import const
import framebuf
from time import sleep

_NOOP = const(0)
_DIGIT0 = const(1)
_DECODEMODE = const(5)
_INTENSITY = const(10)
_SCANLIMIT = const(11)
_SHUTDOWN = const(12)
_DISPLAYTEST = const(15)

class Matrix8x8:
    def __init__(self, spi, cs, num):
        """
        Driver for cascading MAX7219 8x8 LED matrices.
        >>> import max7219
        >>> from machine import Pin, SPI
        >>> spi = SPI(1)
        >>> display = max7219.Matrix8x8(spi, Pin('X5'), 4)
        >>> display.text('1234',0,0,1)
        >>> display.show()
        """
        self.spi = spi
        self.cs = cs
        self.cs.init(cs.OUT, True)
        self.buffer = bytearray(8 * num)
        self.num = num
        fb = framebuf.FrameBuffer(self.buffer, 8 * num, 8, framebuf.MONO_HLSB)
        self.framebuf = fb
        # Provide methods for accessing FrameBuffer graphics primitives. This is a workround
        # because inheritance from a native class is currently unsupported.
        # http://docs.micropython.org/en/latest/pyboard/library/framebuf.html
        self.fill = fb.fill  # (col)
        self.pixel = fb.pixel # (x, y[, c])
        self.hline = fb.hline  # (x, y, w, col)
        self.vline = fb.vline  # (x, y, h, col)
        self.line = fb.line  # (x1, y1, x2, y2, col)
        self.rect = fb.rect  # (x, y, w, h, col)
        self.fill_rect = fb.fill_rect  # (x, y, w, h, col)
        self.text = fb.text  # (string, x, y, col=1)
        self.scroll = fb.scroll  # (dx, dy)
        self.blit = fb.blit  # (fbuf, x, y[, key])
        self.init()

    def _write(self, command, data):
        self.cs(0)
        for m in range(self.num):
            self.spi.write(bytearray([command, data]))
        self.cs(1)

    def init(self):
        for command, data in (
            (_SHUTDOWN, 0),
            (_DISPLAYTEST, 0),
            (_SCANLIMIT, 7),
            (_DECODEMODE, 0),
            (_SHUTDOWN, 1),
        ):
            self._write(command, data)

    def brightness(self, value):
        if not 0 <= value <= 15:
            raise ValueError("Brightness out of range")
        self._write(_INTENSITY, value)

    def show(self):
        for y in range(8):
            self.cs(0)
            for m in range(self.num):
                self.spi.write(bytearray([_DIGIT0 + y, self.buffer[(y * self.num) + m]]))
            self.cs(1)
            
    def draw_circle(self, x0, y0, radius, color):
        x = radius
        y = 0
        err = 0

        while x >= y:
            # Draw the 8 octants of the circle using the pixel() method
            self.pixel(x0 + x, y0 + y, color)
            self.pixel(x0 + y, y0 + x, color)
            self.pixel(x0 - y, y0 + x, color)
            self.pixel(x0 - x, y0 + y, color)
            self.pixel(x0 - x, y0 - y, color)
            self.pixel(x0 - y, y0 - x, color)
            self.pixel(x0 + y, y0 - x, color)
            self.pixel(x0 + x, y0 - y, color)

            y += 1
            if err <= 0:
                err += 2*y + 1
            if err > 0:
                x -= 1
                err -= 2*x + 1

    def draw_8x8_circle(self, x_offset, color=1):
        circle_map = [
            0b00111100, #    **** (Top)
            0b01000010, #   ******
            0b10000001, #  ********
            0b10000001, #  ********
            0b10000001, #  ********
            0b10000001, #  ********
            0b01000010, #   ******
            0b00111100  #    **** (Bottom)
        ]
        
        for y, col in enumerate(circle_map):
            for x in range(8):
                if (col >> (7 - x)) & 1:
                    self.pixel(x + x_offset, y, color)
                    
    def draw_one(self, x, y):
        """
        Draws a 4x6 '1' at the specified top-left (x, y) coordinates.
        Standard size for this function: w=4, h=6.
        """
        # 1. The Main Vertical Stem (The "body" of the 1)
        # We place it at x+2 to leave room for the hook
        self.vline(x + 2, y, 6, 1)
        
        # 2. The Top Hook (The serif)
        self.pixel(x + 1, y + 1, 1)
        self.pixel(x, y + 2, 1) # Optional: makes the hook longer
        
        # 3. The Bottom Base (The stand)
        #self.hline(x+1, y + 5, 3, 1)
        
    def draw_M(self, x, y, col=1):
        self.vline(x, y, 6, col)      # Left leg
        self.vline(x + 4, y, 6, col)  # Right leg
        self.pixel(x + 1, y + 1, col) # Left shoulder
        self.pixel(x + 2, y + 2, col) # Middle point
        self.pixel(x + 3, y + 1, col) # Right shoulder

    def draw_E(self, x, y, col=1):
        self.vline(x, y, 6, col)      # Backbone
        self.hline(x, y, 4, col)      # Top bar
        self.hline(x, y + 2, 3, col)  # Mid bar
        self.hline(x, y + 5, 4, col)  # Bottom bar

    def draw_S(self, x, y, col=1):
        self.hline(x + 1, y, 3, col)  # Top
        self.pixel(x, y + 1, col)     # Top-left
        self.hline(x + 1, y + 2, 2, col) # Mid
        self.pixel(x + 3, y + 3, col) # Right-mid
        self.pixel(x + 3, y + 4, col) # Bottom-right
        self.hline(x, y + 5, 3, col)  # Bottom

    def draw_A(self, x, y, col=1):
        self.vline(x, y + 1, 5, col)  # Left leg
        self.vline(x + 3, y + 1, 5, col) # Right leg
        self.hline(x + 1, y, 2, col)  # Top cap
        self.hline(x, y + 3, 4, col)  # Mid bar

    def draw_X(self, x, y, col=1):
        self.pixel(x, y, col);     self.pixel(x+4, y, col)
        self.pixel(x+1, y+1, col); self.pixel(x+3, y+1, col)
        self.pixel(x+2, y+2, col); self.pixel(x+2, y+3, col)
        self.pixel(x+1, y+4, col); self.pixel(x+3, y+4, col)
        self.pixel(x, y+5, col);   self.pixel(x+4, y+5, col)

    def draw_I(self, x, y, col=1):
        self.vline(x + 1, y, 6, col)  # Stem
        #self.hline(x, y, 3, col)      # Top serif
        #self.hline(x, y + 5, 3, col)  # Bottom serif

    def draw_B(self, x, y, col=1):
        self.vline(x, y, 6, col)
        self.hline(x, y, 3, col); self.hline(x, y+2, 3, col); self.hline(x, y+5, 3, col)
        self.pixel(x+3, y+1, col); self.pixel(x+3, y+3, col); self.pixel(x+3, y+4, col)

    def draw_C(self, x, y, col=1):
        self.vline(x, y+1, 4, col)
        self.hline(x+1, y, 3, col); self.hline(x+1, y+5, 3, col)
        self.pixel(x+3, y+1, col); self.pixel(x+3, y+4, col)

    def draw_D(self, x, y, col=1):
        self.vline(x, y, 6, col)
        self.hline(x, y, 3, col); self.hline(x, y+5, 3, col)
        self.vline(x+3, y+1, 4, col)

    def draw_F(self, x, y, col=1):
        self.vline(x, y, 6, col)
        self.hline(x, y, 4, col); self.hline(x, y+2, 3, col)

    def draw_G(self, x, y, col=1):
        self.vline(x, y+1, 4, col)
        self.hline(x+1, y, 3, col); self.hline(x+1, y+5, 3, col)
        self.vline(x+3, y+3, 2, col); self.pixel(x+2, y+3, col)

    def draw_H(self, x, y, col=1):
        self.vline(x, y, 6, col); self.vline(x+3, y, 6, col)
        self.hline(x+1, y+2, 2, col)

    def draw_J(self, x, y, col=1):
        self.vline(x+2, y, 5, col); self.pixel(x+1, y+5, col); self.pixel(x, y+4, col)

    def draw_K(self, x, y, col=1):
        self.vline(x, y, 6, col)
        self.pixel(x+3, y, col); self.pixel(x+3, y+5, col)
        self.pixel(x+2, y+1, col); self.pixel(x+2, y+4, col)
        self.pixel(x+1, y+2, col); self.pixel(x+1, y+3, col)

    def draw_L(self, x, y, col=1):
        self.vline(x, y, 6, col); self.hline(x+1, y+5, 3, col)

    def draw_O(self, x, y, col=1):
        self.rect(x, y, 4, 6, col)

    def draw_P(self, x, y, col=1):
        self.vline(x, y, 6, col); self.hline(x, y, 3, col)
        self.hline(x, y+2, 3, col); self.pixel(x+3, y+1, col)

    def draw_Q(self, x, y, col=1):
        self.rect(x, y, 4, 5, col)
        self.pixel(x+2, y+4, col); self.pixel(x+3, y+5, col)

    def draw_R(self, x, y, col=1):
        self.draw_P(x, y, col); self.pixel(x+2, y+3, col); self.pixel(x+3, y+4, col); self.pixel(x+3, y+5, col)

    def draw_T(self, x, y, col=1):
        self.hline(x, y, 5, col); self.vline(x+2, y+1, 5, col)

    def draw_U(self, x, y, col=1):
        self.vline(x, y, 5, col); self.vline(x+3, y, 5, col); self.hline(x+1, y+5, 2, col)

    def draw_V(self, x, y, col=1):
        self.vline(x, y, 4, col); self.vline(x+4, y, 4, col)
        self.pixel(x+1, y+4, col); self.pixel(x+3, y+4, col); self.pixel(x+2, y+5, col)

    def draw_W(self, x, y, col=1):
        self.vline(x, y, 5, col); self.vline(x+4, y, 5, col)
        self.pixel(x+1, y+5, col); self.pixel(x+3, y+5, col); self.pixel(x+2, y+4, col)

    def draw_Y(self, x, y, col=1):
        self.pixel(x, y, col); self.pixel(x+4, y, col)
        self.pixel(x+1, y+1, col); self.pixel(x+3, y+1, col)
        self.vline(x+2, y+2, 4, col)

    def draw_Z(self, x, y, col=1):
        self.hline(x, y, 5, col); self.hline(x, y+5, 5, col)
        self.pixel(x+4, y+1, col); self.pixel(x+3, y+2, col)
        self.pixel(x+2, y+3, col); self.pixel(x+1, y+4, col)

    def draw_N(self, x, y, col=1):
        self.vline(x, y, 6, col)      # Left leg
        self.vline(x + 4, y, 6, col)  # Right leg
        self.pixel(x + 1, y + 1, col) # Diagonal step 1
        self.pixel(x + 2, y + 2, col) # Diagonal step 2
        self.pixel(x + 3, y + 3, col) # Diagonal step 3

    def draw_0(self, x, y, col=1):
        self.rect(x, y, 4, 6, col)    # Outer box
        self.pixel(x, y, 0); self.pixel(x+3, y, 0) # Smooth corners
        self.pixel(x, y+5, 0); self.pixel(x+3, y+5, 0)

    def draw_1(self, x, y, col=1):
        self.vline(x + 2, y, 6, col)  # Stem
        self.pixel(x + 1, y + 1, col) # Hook
        self.hline(x + 1, y + 5, 3, col) # Base

    def draw_2(self, x, y, col=1):
        self.hline(x, y, 4, col)      # Top
        self.pixel(x + 3, y + 1, col) # Right shoulder
        self.hline(x, y + 2, 4, col)  # Mid
        self.pixel(x, y + 3, col)     # Left hip
        self.hline(x, y + 5, 4, col)  # Bottom
        self.pixel(x, y + 4, col)     # Extra connector

    def draw_3(self, x, y, col=1):
        self.hline(x, y, 4, col)      # Top
        self.hline(x + 1, y + 2, 3, col) # Mid
        self.hline(x, y + 5, 4, col)  # Bottom
        self.vline(x + 3, y, 6, col)  # Right spine

    def draw_4(self, x, y, col=1):
        self.vline(x, y, 3, col)      # Top-left leg
        self.vline(x + 3, y, 6, col)  # Right spine
        self.hline(x, y + 3, 4, col)  # Crossbar

    def draw_5(self, x, y, col=1):
        self.hline(x, y, 4, col)      # Top
        self.pixel(x, y + 1, col)     # Left shoulder
        self.hline(x, y + 2, 4, col)  # Mid
        self.pixel(x + 3, y + 3, col) # Right hip
        self.hline(x, y + 5, 4, col)  # Bottom
        self.pixel(x + 3, y + 4, col)

    def draw_6(self, x, y, col=1):
        self.vline(x, y, 6, col)      # Backbone
        self.hline(x, y, 4, col)      # Top
        self.rect(x, y + 2, 4, 4, col) # Bottom loop

    def draw_7(self, x, y, col=1):
        self.hline(x, y, 4, col)      # Top
        self.vline(x + 3, y, 3, col)  # Top-right
        self.vline(x + 2, y + 3, 3, col) # Slanted stem

    def draw_8(self, x, y, col=1):
        self.rect(x, y, 4, 3, col)    # Top loop
        self.rect(x, y + 3, 4, 3, col) # Bottom loop

    def draw_9(self, x, y, col=1):
        self.rect(x, y, 4, 4, col)    # Top loop
        self.hline(x, y + 5, 4, col)  # Bottom
        self.vline(x + 3, y, 6, col)  # Right spine
        
    def draw_umlaut_dots(self, x, y, col=1):
            """Helper to draw the two dots above a letter"""
            self.pixel(x + 1, y-1, col)
            self.pixel(x + 2, y-1, col)

    def draw_AE(self, x, y, col=1): # Ä
        self.draw_umlaut_dots(x, y, col)
        # Shifted A (body starts at y+1)
        self.vline(x, y + 2, 4, col)
        self.vline(x + 3, y + 2, 4, col)
        self.hline(x + 1, y + 1, 2, col)
        self.hline(x, y + 3, 4, col)

    def draw_OE(self, x, y, col=1): # Ö
        self.draw_umlaut_dots(x, y, col)
        # Flattened O
        self.rect(x, y + 1, 4, 5, col)

    def draw_UE(self, x, y, col=1): # Ü
        self.draw_umlaut_dots(x, y, col)
        # Shifted U
        self.vline(x, y + 1, 4, col)
        self.vline(x + 3, y + 1, 4, col)
        self.hline(x + 1, y + 5, 2, col)
        
    def draw_clock(self, hours, minutes, show_colon=True):
        self.fill(0) # Clear the screen
        
        # Calculate digits
        h1, h2 = hours // 10, hours % 10
        m1, m2 = minutes // 10, minutes % 10
        
        # Position mapping (Total width used: 27 pixels)
        # H1 at 2, H2 at 8, Colon at 15, M1 at 19, M2 at 25
        
        # Draw Hours
        if h1 > 0: # Don't draw leading zero for hours (e.g. 09:30 -> 9:30)
            self.draw_digit(h1, 2, 1)
        self.draw_digit(h2, 8, 1)
        
        # Draw Colon (Blinking)
        if show_colon:
            self.pixel(15, 2, 1)
            self.pixel(15, 4, 1)
            
        # Draw Minutes
        self.draw_digit(m1, 19, 1)
        self.draw_digit(m2, 25, 1)
        
    def draw_digit(self, val, x, y):
        # Helper to route the value to the correct function
        func_map = [self.draw_0, self.draw_1, self.draw_2, self.draw_3, self.draw_4,
                    self.draw_5, self.draw_6, self.draw_7, self.draw_8, self.draw_9]
        func_map[val](x, y)
    
    def draw_letter(self, char, x, y, col=1, min_x = 8):
            methods = {
                'A': self.draw_A, 'B': self.draw_B, 'C': self.draw_C, 'D': self.draw_D,
                'E': self.draw_E, 'F': self.draw_F, 'G': self.draw_G, 'H': self.draw_H,
                'I': self.draw_I, 'J': self.draw_J, 'K': self.draw_K, 'L': self.draw_L,
                'M': self.draw_M, 'N': self.draw_N, 'O': self.draw_O, 'P': self.draw_P,
                'Q': self.draw_Q, 'R': self.draw_R, 'S': self.draw_S, 'T': self.draw_T,
                'U': self.draw_U, 'V': self.draw_V, 'W': self.draw_W, 'X': self.draw_X,
                'Y': self.draw_Y, 'Z': self.draw_Z,
                '0': self.draw_0, '1': self.draw_1, '2': self.draw_2, '3': self.draw_3,
                '4': self.draw_4, '5': self.draw_5, '6': self.draw_6, '7': self.draw_7,
                '8': self.draw_8, '9': self.draw_9,
                'Ä': self.draw_AE, 'Ö': self.draw_OE, 'Ü': self.draw_UE,
                ' ': lambda x, y, col: None
            }
            
            if char in methods:
                        # ONLY draw if the letter's starting position is past the static box
                        if x >= min_x:
                            methods[char](x, y, col)
            
    def write_text(self, string, x_start, y, col=1, x_space=0, min_x=8):
        cursor_x = x_start
        for char in string:
            self.draw_letter(char, cursor_x, y, col, min_x)
            # Adjust spacing: M and W are 5 wide, others are 4, I is 3
            if char in 'MWNT':
                cursor_x += (6+x_space)
            elif char in 'I':
                cursor_x += (4+x_space)
            else:
                cursor_x += (5+x_space)
        return cursor_x
    
    def scroll_text(self, string, delay_ms=50):
            # Calculate approximate width (most chars are 5-6 pixels wide)
            # For a more accurate measure, you'd track cursor_x in write_text
            text_width = len(string) * 6 
            
            # Start text just off the right edge (32)
            # Scroll until it's completely off the left edge (-text_width)
            for i in range(32, -text_width, -1):
                self.fill(0)
                self.write_text(string, i, 1)
                self.show()
                sleep(delay_ms / 1000)
                
    def alert_animation(self, text):
        """Flashes the text to grab attention."""
        for _ in range(4):
            # Flash ON
            self.fill(0)
            self.rect(0, 0, 32, 8, 1) # Draw a border
            self.write_text(text, 4, 1)
            self.show()
            sleep(0.2)
            # Flash OFF
            self.fill(0)
            self.show()
            sleep(0.1)
            
    def draw_1_thin(self, x, y, col=1):
            """A thinner '1' for fitting inside circles."""
            self.vline(x + 2, y, 6, col)
            self.pixel(x + 1, y + 1, col)

    def scroll_text_split(self, string, delay_ms=45, scroll_start=8):
            # Sanitize the string to handle Unicode escapes from the API
            string = sanitize_direction(string)
            
            # Calculate width for the loop (approx 6px per char)
            text_width = 0
            for char in string:
                if char in 'MWÄÖÜ': text_width += 6
                elif char in 'I1': text_width += 4
                else: text_width += 5
                
            # i is the starting x-position of the string
            # We start at 32 (right edge) and scroll until text clears the 8px boundary
            for i in range(32, scroll_start - text_width, -1):
                # 1. Clear ONLY the scrolling area (Panels 2, 3, 4)
                self.fill_rect(scroll_start, 0, 24, 8, 0)
                
                # 2. Draw the scrolling text
                # The clip in draw_letter (if x >= 8) ensures it stays out of Panel 1
                self.write_text(string, i, 1)
                
                # 3. Draw Static Icon on Panel 1
                # We clear the panel first to ensure no text "ghosts" are behind it
                self.fill_rect(0, 0, 8, 8, 0) 
                self.draw_8x8_circle(0) # Your circle function at x=0
                self.draw_one(2, 1)      # Your number 1 function at (2,1)
                
                self.show()
                sleep(delay_ms / 1000)
                
    def scroll_text_split_rect(self, line, string, delay_ms=45, scroll_start=13):
            string = sanitize_direction(string)
            
            # Calculate width
            text_width = 0
            for char in string:
                if char in 'MWÄÖÜ': text_width += 6
                elif char in 'I1': text_width += 4
                else: text_width += 5
                
            for i in range(32, scroll_start - text_width, -1):
                # 1. Clear the WHOLE screen for a fresh frame
                self.fill(0)
                
                # 2. Draw the scrolling text with CLIPPING at scroll_start
                # Passing scroll_start as min_x ensures letters don't appear in the box
                self.write_text(string, i, 1, 1, min_x=scroll_start)
                
                # 3. Draw Static Box (drawn LAST so it is always on top)
                # Clear the box area first just in case
                self.fill_rect(0, 0, 11, 8, 0) 
                
                # Draw digits for the line number
                self.write_text(str(line), 1, 1, min_x=1)
                
                # Draw Rectangle Frame (0 to 10 is 11 pixels wide)
                self.vline(0, 0, 8, 1)    # Left
                self.hline(1, 0, scroll_start-3, 1)   # Top
                self.vline(scroll_start-3, 0, 8, 1)   # Right (moved to 11 to fit two digits)
                self.hline(1, 7, scroll_start-3, 1)   # Bottom
                
                self.show()
                sleep(delay_ms / 1000)

    def slow_flash_time(self, mins_text):
        """Slowly flashes the arrival time for 3 seconds."""
        for _ in range(3): # 3 cycles = ~3 seconds
            # Show
            self.fill_rect(8, 0, 24, 8, 0)
            self.draw_8x8_circle(0)
            self.draw_one(2, 1)
            self.write_text(mins_text, 10, 1)
            self.show()
            sleep(0.7)
            # Hide text only
            self.fill_rect(8, 0, 24, 8, 0)
            self.show()
            sleep(0.3)
            
def sanitize_direction(text):
        # Mapping the common VAG API hex codes to actual characters
        # \xfc = ü, \xf6 = ö, \xe4 = ä, \xdf = ß
        text = text.replace('\xfc', 'Ü').replace('\xf6', 'Ö').replace('\xe4', 'Ä')
        text = text.replace('\xdc', 'Ü').replace('\xd6', 'Ö').replace('\xc4', 'Ä')
        # Optional: Replace 'ß' with 'SS' as it's hard to draw in 6px
        text = text.replace('\xdf', 'SS') 
        return text.upper()

