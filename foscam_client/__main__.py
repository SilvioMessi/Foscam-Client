from foscam_client import FoscamClient, FoscamThread
import settings as settings


if __name__ == "__main__":
    foscam_client = FoscamClient(settings.IP, settings.PORT, settings.USERNAME, settings.PASSWORD, settings.STORE_RECORDS_DIRECTORY)
    keep_alive_tread = FoscamThread(foscam_client, 'keep-alive')
    keep_alive_tread.start()
    motion_detection_tread = FoscamThread(foscam_client, 'motion detection')
    motion_detection_tread.start()
    motion_detection_record_tread = FoscamThread(foscam_client, 'record')
    motion_detection_record_tread.start()
