# Foscam Client #

Client for Foscam HD cameras that use low level proprietary protocol.
Tested on Foscam FI9816P V2.
Developed starting from the information reported [here](https://github.com/MStrecke/pyFosControl/blob/master/lowlevel/LowlevelProtocol.md).
For the moment the client:
* connects to the camera
* keep-alive the camera
* listens to motion detection signals from the camera (if motion detection is enable on the camera)
* when a motion detection occurred, record a raw h264 video and split them in JPEG frames (using FFmpeg)


## Requirements ##

* [Python](https://www.python.org/) 2.7
* [pip](https://pypi.python.org/pypi/pip)
* [virtualenv](https://pypi.python.org/pypi/virtualenv)
* [FFmpeg](https://www.ffmpeg.org/)

## Installation ##

* ``` $ git clone https://github.com/SilvioMessi/Foscam-Client.git ```
* ``` $ cd Foscam-Client/ ```
* ``` $ virtualenv -p /path/to/python2.7 ENV ```
* ``` $ source ENV/bin/activate ```
* ``` (ENV)$ pip install -r requirements.txt ```
* edit the file foscam_client/settings.py with your settings
* ``` (ENV)$ python foscam_client ```

