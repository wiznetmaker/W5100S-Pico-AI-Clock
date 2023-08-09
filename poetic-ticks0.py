from usocket import socket
from machine import ADC, Pin,SPI
import network
import time
import utime
import urequests
import ujson
from time import sleep
import array
import binascii
import ntptime
from ili9341 import Display, color565
from xglcd_font import XglcdFont
INTERVAL_1_MINUTE = 6000 # for test purposes
INTERVAL_15_MINUTES = 900000  # 900,000 milliseconds = 15 minutes
INTERVAL_1_HOUR = 3600000     # 3,600,000 milliseconds = 1 hour
UTC_OFFSET = 9 * 60 * 60
def display_init():
    # Baud rate of 40000000 seems about the max
    displayspi = SPI(1, baudrate=40_000_000, sck=Pin(10), mosi=Pin(11))
    display = Display(displayspi, dc=Pin(4), cs=Pin(3), rst=Pin(2),rotation=180)
       
    return display

def staticDisplay(display, font, temp):

    display.draw_text(50, 0, 'POETIC TICKS', font,
                      color565(255, 128, 0))
    display.draw_text(5, 40, 'RPi Pico, WIZnet and', font,
                      color565(255, 128, 0))
    display.draw_text(5, 70, 'ChatGPT Cooperation', font,
                      color565(255, 128, 0))
    year, month, day, hour, minute, second, _, _ = time.localtime(time.time() + UTC_OFFSET)
    display.draw_text(60, 110, "{:04d}-{:02d}-{:02d}".format(year, month, day), font,
                      color565(0, 128, 255))
    display.draw_text(80, 150, "{:02d}:{:02d}:{:02d}".format(hour, minute, second), font,
                      color565(0, 128, 255))
    display.draw_text(50, 210, "Current temp:", font,
                      color565(0, 128, 0))
    display.draw_text(60, 250, "{:.2f} deg C".format(temp), font,
                      color565(0, 128, 0))
 
def draw_long_text(display, font, text):
    textlines = text.split("\n")
    line_height = 25  # Adjust line height according to your font
    y=0
    for textline in textlines:
        line = ""
        if len(textline) <=20:
            display.draw_text(0, y, textline, font, color565(255, 255, 255))
            y += line_height + 10

        else:
            words = textline.split()
            for word in words:
                if (len(line) + len(word)) <= 20:
                    line += word + " "
                else:
                    display.draw_text(0, y, line, font, color565(255, 255, 255))
                    y += line_height
                    line = word + " "
                
                display.draw_text(0, y, line, font, color565(255, 255, 255))
            y += line_height + 10
   
#W5x00 chip init
def w5x00_init():
    spi=SPI(0,2_000_000, mosi=Pin(19),miso=Pin(16),sck=Pin(18))
    nic = network.WIZNET5K(spi,Pin(17),Pin(20)) #spi,cs,reset pin
    nic.active(True)
    nic.ifconfig(('192.168.11.30','255.255.255.0','192.168.11.1','8.8.8.8'))
    while not nic.isconnected():
        time.sleep(1)
        print(nic.regs())
    print(nic.ifconfig())

def chatgpt_request(open_ai_question):
    url = "https://api.openai.com/v1/chat/completions"
    
    instructions = "Do not use emojis."
    character_limit = "Max 200 characters"
    api_key = "API_KEY_HERE"

    payload = ujson.dumps({
      "model": "gpt-3.5-turbo",
      "messages": [
        {
          "role": "system", "content": ""},
        {
          "role": "user",
          "content": open_ai_question + instructions + character_limit
        },
      ],
      "temperature": 1,
      "top_p": 1,
      "n": 1,
      "stream": False,
      "max_tokens": 230,
      "presence_penalty": 0,
      "frequency_penalty": 0
    })

    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + api_key
    }
    
    len_con = False
    while not (len_con == True):
        # Post Data
        response = urequests.post(url, headers=headers, data=payload)
        response_data = response.json()
        # Access JSON object
        open_ai_message = response_data["choices"][0]["message"]["content"]
        # Close the connection
        response.close()
        #print(open_ai_message)
        if (len(open_ai_message) <= 200):
           len_con = True
        else:
           print("ChatGPT response too long (", len(open_ai_message),"). Resending. Please wait!")
    
    return open_ai_message

def main():
    w5x00_init()
    myDisplay = display_init()
    ntptime.host = "2.asia.pool.ntp.org"
    
    print("Local time before synchronization：%s" %str(time.localtime()))
    #make sure to have internet connection
    ntptime.settime()
    print("Local time after synchronization：%s" %str(time.localtime()))
    
    adc = machine.ADC(4)
    
    print('Loading unispace')
    unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)
    print('Fonts loaded.')
    
    timePrompt = "generate funny tiny poem that tells the time "
    jokePrompt = "generate a funny hilarious IT fact"
    
    last_15_minutes_request = utime.ticks_ms()
    last_hour_request = utime.ticks_ms()
    while True:
        current_time = utime.ticks_ms()
        year, month, day, hour, minute, second, _, _ = time.localtime(time.time() + UTC_OFFSET)
        
        ADC_voltage = adc.read_u16() * (3.3 / (65535))
        temperature_celcius = 27 - (ADC_voltage - 0.706)/0.001721
        
        # Make HTTP request every 15 minutes
        if current_time - last_15_minutes_request >= INTERVAL_15_MINUTES:
            myDisplay.clear()
            text = chatgpt_request(timePrompt+"{:02d}:{:02d}".format(hour, minute))
            draw_long_text(myDisplay, unispace, text)
            last_15_minutes_request = current_time
            sleep(10)
            myDisplay.clear()
        # Make HTTP request every hour
        if current_time - last_hour_request >= INTERVAL_1_HOUR:
            myDisplay.clear()
            text = chatgpt_request(jokePrompt)
            draw_long_text(myDisplay, unispace, text)
            last_hour_request = current_time      
            sleep(10)
            myDisplay.clear()
            
        staticDisplay(myDisplay, unispace, temperature_celcius)
        
if __name__ == "__main__":
    main()

