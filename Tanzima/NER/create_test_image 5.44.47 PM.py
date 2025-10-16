#!/usr/bin/env python3
"""
Create a simple test image for object detection
"""
import cv2
import numpy as np

# Create a simple test image (640x480)
img = np.ones((480, 640, 3), dtype=np.uint8) * 255

# Draw some shapes that look like objects
# Draw a rectangle (simulating a person)
cv2.rectangle(img, (200, 100), (280, 350), (100, 100, 100), -1)
cv2.circle(img, (240, 130), 30, (150, 150, 150), -1)  # head

# Draw a small rectangle (simulating an object)
cv2.rectangle(img, (250, 250), (300, 280), (50, 50, 200), -1)

# Add text
cv2.putText(img, "Test Image", (220, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

# Save the image
cv2.imwrite("uploads/test1.jpg", img)
print("Created test image: uploads/test1.jpg")

