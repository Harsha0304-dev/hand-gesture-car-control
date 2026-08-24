# 🎮 Virtual Steering Wheel

### Control a racing game using your hands — no physical steering wheel required.

**Virtual Steering Wheel** is a real-time computer vision project that transforms natural hand movements into a virtual Xbox controller.

Using a webcam and **MediaPipe**, the system tracks both hands, detects hand gestures, calculates the steering angle from wrist positions, and translates these movements into steering, acceleration, and braking controls.

---

## 🚗 How It Works

The system follows this pipeline:

```text
Webcam
   ↓
OpenCV Video Capture
   ↓
MediaPipe Hand Tracking
   ↓
Hand Landmark Detection
   ↓
Gesture & Wrist-Angle Analysis
   ↓
Steering / Throttle / Brake
   ↓
Virtual Xbox 360 Controller
   ↓
Racing Game
```

The project detects up to **two hands** and uses their wrist positions to determine the steering direction and intensity.

---

## ✋ Gesture Controls

| Gesture                           | Action                        |
| --------------------------------- | ----------------------------- |
| 👊 Both fists                     | Accelerate                    |
| 👊 Both fists + tilt left         | Accelerate + steer left       |
| 👊 Both fists + tilt right        | Accelerate + steer right      |
| 🖐️ Both hands open               | Brake                         |
| 🖐️ Both hands open + tilt left   | Brake + steer left            |
| 🖐️ Both hands open + tilt right  | Brake + steer right           |
| 👊 + 🖐️ One fist + one open hand | Neutral / Coast               |
| No hands detected                 | Release all controller inputs |

> **Note:** Steering works independently of acceleration and braking, allowing the car to turn while accelerating or braking.

---

## 🧠 Core Technology

### MediaPipe Hand Tracking

MediaPipe detects hand landmarks from the webcam feed and provides the coordinates required for gesture recognition and steering calculations.

### Wrist-Angle Steering

The system calculates the angle between the left and right wrists using their detected positions.

Small movements around the center are ignored using a **dead zone** to reduce unwanted steering jitter.

The steering value is then converted into an analog value between **-1 and +1** and sent to the virtual controller's left joystick.

### Gesture-Based Throttle & Brake

The system checks the number of extended fingers on each hand.

* **Both fists → Accelerator**
* **Both open hands → Brake**
* **One fist + one open hand → Neutral**

The accelerator and brake are mapped to the virtual Xbox controller's analog triggers.

---

## 🎮 Virtual Xbox Controller

Instead of physically pressing keyboard keys, this project creates a **virtual Xbox 360 controller** using `vgamepad`.

The controller provides:

* 🎮 Analog steering
* ⚡ Analog acceleration
* 🛑 Analog braking
* 🔄 Real-time controller updates

This allows the project to work with games that support Xbox/controller input.

---

## 🧠 Technologies Used

| Technology    | Purpose                              |
| ------------- | ------------------------------------ |
| **Python**    | Core application                     |
| **MediaPipe** | Real-time hand tracking              |
| **OpenCV**    | Webcam capture and visual processing |
| **NumPy**     | Numerical calculations and smoothing |
| **vgamepad**  | Virtual Xbox 360 controller          |
| **Webcam**    | Real-time input                      |

---

## 📋 Requirements

Before running the project, make sure you have:

* Python 3.9+
* A working webcam
* Windows or macOS
* A racing game that supports controller input

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/Harsha0304-dev/hand-gesture-car-control.git
cd hand-gesture-car-control
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Or install them manually:

```bash
pip install mediapipe opencv-python numpy vgamepad
```

---

## ▶️ Run the Project

Start the virtual steering wheel:

```bash
python steering_wheel.py
```

The webcam window will open and begin tracking your hands.

Place both hands in front of the webcam as if you are holding a steering wheel.

Press **Q** to exit.

---

## 🪟 Windows Setup

The project automatically selects the appropriate OpenCV camera backend for Windows.

### 1. Install Python

Install Python 3.9 or newer.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python steering_wheel.py
```

### 4. Camera not detected?

Open `steering_wheel.py` and change:

```python
CAMERA_INDEX = 0
```

Try:

```python
CAMERA_INDEX = 1
```

or:

```python
CAMERA_INDEX = 2
```

> If Windows asks for camera permission, allow Python to access your camera.

---

## 🍎 macOS Setup

The project was originally developed and tested on **macOS with Apple M2**.

macOS requires camera permission for applications using the webcam.

Go to:

**System Settings → Privacy & Security → Camera**

Enable camera access for the application running Python.

---

## 🎛️ Configuration

The following settings can be adjusted at the top of `steering_wheel.py`.

| Setting              | Default | Description                              |
| -------------------- | ------: | ---------------------------------------- |
| `CAMERA_INDEX`       |     `0` | Webcam index                             |
| `DEAD_ZONE_DEG`      |     `5` | Steering dead zone                       |
| `RELEASE_ZONE_DEG`   |     `3` | Steering release zone                    |
| `MAX_STEER_DEG`      |    `32` | Maximum steering angle                   |
| `STEERING_CURVE`     |  `0.70` | Steering sensitivity curve               |
| `FLIP_CAMERA`        |  `True` | Mirrors the webcam feed                  |
| `GRACE_FRAMES`       |     `8` | Delay before releasing controls          |
| `OPEN_FINGER_THRESH` |     `3` | Fingers required for open-hand detection |

---

## 📊 Real-Time HUD

The application provides a visual dashboard displaying:

* Steering direction
* Steering angle
* Steering percentage
* Accelerator / brake status
* Left-hand state
* Right-hand state
* FPS
* Hand detection status
* Virtual steering wheel visualization

This provides immediate feedback while controlling the game.

---

## 🛡️ Safety Handling

If both hands disappear from the camera view, the system waits for a short grace period and then releases the controller inputs.

This prevents the virtual controller from remaining stuck in an acceleration, braking, or steering state.

---

## 🎮 Compatible Games

The controller can be used with racing games that support Xbox/controller input.

The project also includes a controller implementation designed for **CrazyGames racing gameplay**.

Example use cases include:

* 🏎️ Browser racing games
* 🎮 PC racing games
* 🏁 Controller-supported racing games
* 🚗 CrazyGames racing titles

---

## 💡 Key Features

* ✋ Hands-free racing control
* 📷 Real-time webcam processing
* 🧠 MediaPipe hand tracking
* 👋 Gesture-based acceleration and braking
* ↔️ Analog steering using wrist-angle detection
* 🎮 Virtual Xbox 360 controller
* ⚡ Real-time response
* 📊 Live performance HUD
* 🎛️ Configurable steering sensitivity
* 🛡️ Automatic controller input release
* 💻 Windows and macOS support

---

## 📁 Project Structure

```text
hand-gesture-car-control/
│
├── steering_wheel.py
├── hand_crazygames_controller.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🚀 Future Improvements

Possible future enhancements include:

* More advanced hand gestures
* Custom gesture profiles
* Adjustable controller mappings
* Speed estimation
* Voice-controlled features
* Game-specific control profiles
* Additional controller support
* Improved gesture classification
* More advanced computer vision features

---

## 👨‍💻 Author

**B. Sri Harsha**

Built as an exploration of:

**Computer Vision • Human-Computer Interaction • Gesture Recognition • Real-Time Game Control**

---

## ⭐ Support

If you find this project interesting, consider giving the repository a ⭐ on GitHub.

**Repository:**
https://github.com/Harsha0304-dev/hand-gesture-car-control
