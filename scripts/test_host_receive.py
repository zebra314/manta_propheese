import cv2

cap = cv2.VideoCapture("udp://0.0.0.0:5000", cv2.CAP_FFMPEG)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame missing")
        continue
    
    cv2.imshow("Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break