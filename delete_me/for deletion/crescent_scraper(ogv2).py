from datetime import datetime,timedelta #for setting times
import pytz  # Import pytz for timezone handling
import csv #to export to csv file
import requests #to get web pages
from PIL import Image  #to manipulate image
import PIL.ImageOps #to manipulate image
import cv2 #to manipulate image
import pytesseract #to ocr read from image
import re #to use filtering numbers from string
from bs4 import BeautifulSoup #for parsing website
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import hashlib #for creating md5 hash
import os # os to allow for dir/folder management

# Define the base directory for the scraper
base_dir = "/Users/jayriihiluoma/Documents/python/scrapers/crescent_scraper"

# Create an 'images' folder inside the scraper folder
images_dir = os.path.join(base_dir, "images")
os.makedirs(images_dir, exist_ok=True)

# Define the timezone for Bermuda (you can use "America/Halifax" as it's the same)
timezone = pytz.timezone("America/Halifax")

# Get the current time in the Bermuda timezone
now_time_bda = datetime.now(timezone)
now_time = now_time_bda.strftime("%Y-%m-%d-%H%M")  # For filenames or identifiers
#print (("writing_crescent_v1 {}").format(now_time))


URLC = 'http://weather.bm/tools/graphics.asp?name=CRESCENT%20GRAPH&user='
page = requests.get(URLC)
#print (type(page))
#if (type(page)) == requests.models.Response:
    #print ('page type ok')
#else:
    #print ('page type wrong')

soup = BeautifulSoup(page.content, 'html.parser')


images = soup.find(id="image")
src = images.get('src')
    #print(src)
url = ('http://weather.bm/{}').format(src)
url1 = url.replace(" ", "%20")

filename = os.path.join(images_dir, "windc.png")
#filename = 'windv3 {}.png'.format(now_time)
r = requests.get(url1)
open(filename, 'wb').write(r.content)

im = Image.open(filename, mode='r')
#im.show()

# Setting the points for cropped image wind speed
left = 980
top = 82
right =1140
bottom = 112

# Cropped image of above dimension 
# (It will not change orginal image) 
im1 = im.crop((left, top, right, bottom)) 
# Save the cropped image in the nmb_scraper folder
crop_wspc_path = os.path.join(images_dir, "crop_wspc.png")
im1.save(crop_wspc_path)

# Open the cropped image
cropwspc = Image.open(crop_wspc_path)
# Uncomment if you want to display the image
# cropwspc.show()

# Convert the cropped image to grayscale
bw_crop_wspc_path = os.path.join(images_dir, "bw_crop_wspc.png")
image_file = cropwspc.convert('L')  # convert image to black and white
image_file.save(bw_crop_wspc_path)

# Invert the grayscale image to create a black-and-white inverted image
bw_crop_inv_wspc_path = os.path.join(images_dir, "bw_crop_inv_wspc.png")
image = Image.open(bw_crop_wspc_path)
inverted_image = PIL.ImageOps.invert(image)
inverted_image.save(bw_crop_inv_wspc_path)

# Uncomment if you want to display the inverted image
# inverted_image.show()

# Read the inverted image with OpenCV
img = cv2.imread(bw_crop_inv_wspc_path)

# Perform OCR using pytesseract
text_ws = pytesseract.image_to_string(img)

# Output the OCR result
#print(text_ws)
'''im1 = im1.save("crop_wspc.png")
cropwspc = Image.open("crop_wspc.png")
#cropwspc.show()

#convert image type
image_file = Image.open("crop_wspc.png") # open colour image
image_file = image_file.convert('L') # convert image to black and white
image_file.save('bw_crop_wspc.png')

#invert image to B&W
image = Image.open('bw_crop_wspc.png')
inverted_image = PIL.ImageOps.invert(image)
inverted_image.save('bw_crop_inv_wspc.png')
#inverted_image.show() 
#read image
img = cv2.imread('bw_crop_inv_wspc.png')
text_ws = pytesseract.image_to_string(img)'''

#print(text_ws)
p = re.compile(r'\d+\.\d+')  # Compile a pattern to capture float values
num_ws = [float(i) for i in p.findall(text_ws)]  # Convert strings to float
recent_ws = num_ws [0]
#print(recent_ws)



#Setting the points for cropped image max wind speed
left = 980
top = 315
right =1140
bottom = 338

# Cropped image of above dimension 
# (It will not change orginal image) 
im1 = im.crop((left, top, right, bottom)) 
# Save the cropped image in the nmb_scraper folder
crop_mwspc_path = os.path.join(images_dir, "crop_mwspc.png")
im1.save(crop_mwspc_path)

# Open the cropped image
cropmwspc = Image.open(crop_mwspc_path)
# Uncomment if you want to display the image
#cropmwspc.show()

# Convert the cropped image to grayscale
bw_crop_mwspc_path = os.path.join(images_dir, "bw_crop_mwspc.png")
image_file = cropmwspc.convert('L')  # convert image to black and white
image_file.save(bw_crop_mwspc_path)

# Invert the grayscale image to create a black-and-white inverted image
bw_crop_inv_mwspc_path = os.path.join(images_dir, "bw_crop_inv_mwspc.png")
image = Image.open(bw_crop_mwspc_path)
inverted_image = PIL.ImageOps.invert(image)
inverted_image.save(bw_crop_inv_mwspc_path)

# Uncomment if you want to display the inverted image
# inverted_image.show()

# Read the inverted image with OpenCV
img = cv2.imread(bw_crop_inv_mwspc_path)

# Perform OCR using pytesseract
text_mws = pytesseract.image_to_string(img)

# Output the OCR result
#print(text_mws)
'''im1 = im1.save("crop_mwspc.png")
cropmwspc = Image.open("crop_mwspc.png")
#cropmwspc.show()

#convert image type
image_file = Image.open("crop_mwspc.png") # open colour image
image_file = image_file.convert('L') # convert image to black and white
image_file.save('bw_crop_mwspc.png')

#invert image to B&W
image = Image.open('bw_crop_mwspc.png')
inverted_image = PIL.ImageOps.invert(image)
inverted_image.save('bw_crop_inv_mwspc.png')
#inverted_image.show() 
#read image
img = cv2.imread('bw_crop_inv_mwspc.png')
text_mws = pytesseract.image_to_string(img)'''

#print(text_mws)

p = re.compile(r'\d+\.\d+')  # Compile a pattern to capture float values
num_mws = [float(i) for i in p.findall(text_mws)]  # Convert strings to float
#print(num_mws)


recent_mws = num_mws[0]

#print(recent_mws)

# Setting the points for cropped image wind direction 
left = 980
top = 535
right =1140
bottom = 565

# Cropped image of above dimension 
# (It will not change orginal image) 
im1 = im.crop((left, top, right, bottom))
# Save the cropped image in the nmb_scraper folder
crop_wdc_path = os.path.join(images_dir, "crop_wdc.png")
im1.save(crop_wdc_path)

# Open the cropped image
cropwdc = Image.open(crop_wdc_path)
# Uncomment if you want to display the image
# cropwdc.show()

# Convert the cropped image to grayscale
bw_crop_wdc_path = os.path.join(images_dir, "bw_crop_wdc.png")
image_file = cropwdc.convert('L')  # convert image to black and white
image_file.save(bw_crop_wdc_path)

# Invert the grayscale image to create a black-and-white inverted image
bw_crop_inv_wdc_path = os.path.join(images_dir, "bw_crop_inv_wdc.png")
image = Image.open(bw_crop_wdc_path)
inverted_image = PIL.ImageOps.invert(image)
inverted_image.save(bw_crop_inv_wdc_path)

# Uncomment if you want to display the inverted image
# inverted_image.show()

# Read the inverted image with OpenCV
img = cv2.imread(bw_crop_inv_wdc_path)

# Perform OCR using pytesseract
text_wd = pytesseract.image_to_string(img)

# Output the OCR result
#print(text_wd)
 

'''# Shows the image in image viewer 
#im1.show() 
im1 = im1.save("crop_wdc.png")

#convert image type
image_file = Image.open("crop_wdc.png") # open colour image
image_file = image_file.convert('L') # convert image to black and white
image_file.save('bw_crop_wdc.png')

#invert image to B&W
#from PIL import Image
#import PIL.ImageOps    

image = Image.open('bw_crop_wdc.png')
#image.show()

inverted_image = PIL.ImageOps.invert(image)
inverted_image.save('bw_crop_inv_wdc.png')

img = cv2.imread("bw_crop_inv_wdc.png")
text_wd = pytesseract.image_to_string(img)'''

#returning only floating numbers from wd string
p = re.compile(r'\d+\.\d+')  # Compile a pattern to capture float values
num_wd = [float(i) for i in p.findall(text_wd)]  # Convert strings to float
#print (num_wd)

#slice for output
recent_wd = num_wd[0]

#print(recent_wd)

    #the 'a' says to append where as a 'w' would write (from scratch)
    #for textLine in text:
    #f.write(textLine) # write data line to the open file 
    # with closes file automatically on exiting block


'''with open('jdatap3.csv', 'a', newline='') as file:  
    writer = csv.writer(file)
    writer.writerow([now_time,recent_ws,recent_mws,recent_wd])
    #print ("finished_writing_pearl V3")'''

#adding date format that GSheets can read with date/time value


#this sets the time to BDA from UTC use timedelta -180 for daylight savings and -240 for no daylight savings
# Format the time for Google Sheets with proper timezone adjustment
now_time_gsheet = now_time_bda.strftime("%Y/%m/%d %H:%M")

#print("This is the time for gsheet recording", now_time_gsheet)	

# Values fetched from Crescent scraping process
print(recent_ws, recent_mws, recent_wd)

# Gsheet APIs
scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("/Users/jayriihiluoma/Documents/python/scrapers/crescent_scraper/creds.json", scope)
client = gspread.authorize(creds)

# Access the Crescent data sheet
sheet = client.open("crescent_data").sheet1

# Fetch the most recent row (row 4) from the Crescent sheet
latest_crescent_row = sheet.row_values(4)

# Compare current values with the most recent row in the sheet
if (
    float(latest_crescent_row[1]) == recent_ws and
    float(latest_crescent_row[2]) == recent_mws and
    float(latest_crescent_row[3]) == recent_wd
):
    print("Crescent data appears to be offline. Switching to pred_cres data.")
    
    # Access pred_cres sheet and fetch the latest row
    pred_sheet = client.open("crescent_data").worksheet("pred_cresc")
    latest_pred_row = pred_sheet.row_values(4)

    # Use pred_cres data for Windguru API
    pred_ws = float(latest_pred_row[1])
    pred_mws = float(latest_pred_row[2])
    pred_wd = float(latest_pred_row[3])

    # Use Crescent scraped data for `Sheet1` (but without substitution)
    data_row_add = [now_time_gsheet, recent_ws, recent_mws, recent_wd]
    print("Inserting Crescent data into Crescent sheet.")
    sheet.insert_row(data_row_add, 4)

    # Use `pred_cres` data for Windguru
    recent_ws = pred_ws
    recent_mws = pred_mws
    recent_wd = pred_wd
else:
    print("Crescent data is online. Using Crescent data.")
    
    # Prepare data for Google Sheets
    data_row_add = [now_time_gsheet, recent_ws, recent_mws, recent_wd]
    print("Inserting Crescent data into Crescent sheet.")
    sheet.insert_row(data_row_add, 4)

print(f"Data being sent to Windguru (from pred_cres if offline): Avg Wind Speed: {recent_ws}, Max Wind Speed: {recent_mws}, Wind Direction: {recent_wd}")

# Creating URL for Windguru API
str2hash = f"{now_time}crescent_bermudacrescentstation*"
result = hashlib.md5(str2hash.encode())
hash_value = result.hexdigest()

# Send data to Windguru
URL = (
    f"http://www.windguru.cz/upload/api.php?"
    f"uid=crescent_bermuda&salt={now_time}&hash={hash_value}&"
    f"wind_avg={recent_ws}&wind_max={recent_mws}&wind_direction={recent_wd}"
)

try:
    response = requests.get(URL)
    print(f"Windguru API Response: {response.status_code}")
except Exception as e:
    print(f"Error occurred while sending data to Windguru: {e}")





'''#Gsheet APIs commented out for working on locally
scope = ['https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("/Users/jayriihiluoma/Documents/python/scrapers/crescent_scraper/creds.json",scope)

client = gspread.authorize(creds)

sheet = client.open("crescent_data").sheet1

data = sheet.get_all_records(head=3)

data_row_add = [now_time_gsheet,recent_ws,recent_mws,recent_wd]
#print("Data to insert:", data_row_add)

sheet.insert_row(data_row_add,4)

# Creating url for windguru get API # initializing string 
str2hash = (("{}crescent_bermudacrescentstation*").format(now_time))
#print(("{}crescent_bermudacrescentstation*").format(now_time))
# encoding Salt using encode() 
# then sending to md5() 
result = hashlib.md5(str2hash.encode()) 
  
# printing the equivalent hexadecimal value. 
#print("The hexadecimal equivalent of hash is : ", end ="") 
#print(result.hexdigest())

#print(("windguru.cz/upload/api.php?uid=crescent_bermuda&salt={}&hash={}&wind_avg={}&wind_max={}&wind_direction={}").format(now_time,result.hexdigest(),recent_ws,recent_mws,recent_wd))

#send windguru pearl data via get
URL = ("http://www.windguru.cz/upload/api.php?uid=crescent_bermuda&salt={}&hash={}&wind_avg={}&wind_max={}&wind_direction={}").format(now_time,result.hexdigest(),recent_ws,recent_mws,recent_wd)
page = requests.get(URL)'''


