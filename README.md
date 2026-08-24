# 🎮 Virtual Steering Wheel

### Control a car game using your hands — no physical steering wheel required.

**Virtual Steering Wheel** is a computer-vision-based project that uses **MediaPipe, Python, and your webcam** to detect hand gestures and convert them into keyboard controls for racing and car games.

Simply place both hands in front of the webcam as if you are holding a steering wheel. Your hand position and gesture determine whether the car accelerates, brakes, or turns.

---

## 🚗 How It Works

The webcam continuously captures your hand movements.

The system uses **MediaPipe** to detect your hands and analyze:

* Hand position
* Hand orientation
* Finger extension
* Left/right steering direction
* Fist vs. open-hand gestures

These movements are then converted into keyboard inputs using **Pynput**.

```text
Webcam
   ↓
Hand Detection
   ↓
MediaPipe
   ↓
Gesture & Tilt Analysis
   ↓
Keyboard Control
   ↓
Car Game
```

---

## ✋ Gesture Controls

| Hand Gesture                    | Car Action               | Keyboard Input |
| ------------------------------- | ------------------------ | -------------- |
| 👊 Both fists, hands level      | Accelerate               | ↑              |
| 👊 Both fists, tilt left        | Accelerate + steer left  | ↑ + ←          |
| 👊 Both fists, tilt right       | Accelerate + steer right | ↑ + →          |
| 🖐️ Both hands open, level      | Brake                    | ↓              |
| 🖐️ Both hands open, tilt left  | Brake + steer left       | ↓ + ←          |
| 🖐️ Both hands open, tilt right | Brake + steer right      | ↓ + →          |
| 👊🖐️ One fist + one open hand  | Neutral                  | —              |
| No hands detected               | Release all keys         | —              |

> **Note:** Steering can be performed while accelerating or braking, allowing simultaneous steering and throttle/brake control.

---

## 🧠 Technologies Used

* **Python 3.9+**
* **MediaPipe** — real-time hand tracking and landmark detection
* **OpenCV** — webcam capture and image processing
* **Pynput** — keyboard control
* **NumPy** — numerical calculations
* **Webcam** — input device

---

## 📋 Requirements

Before running the project, make sure you have:

* Python **3.9 or higher**
* A working webcam
* A racing/car game controlled using keyboard arrow keys

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/Harsha0304-dev/hand-gesture-car-control.git
cd hand-gesture-car-control
```

Install the required dependencies:

```bash
pip install mediapipe opencv-python pynput numpy
```

Or install them using the requirements file:

```bash
pip install -r requirements.txt
```

---

## ▶️ Run the Project

Start the virtual steering wheel:

```bash
python steering_wheel.py
```

A camera window will open and begin detecting your hands.

Press **Q** while the camera window is active to exit the program.

---

## 🪟 Windows Setup

The project supports Windows and automatically selects the appropriate camera backend.

No manual backend modification is required.

### Steps

**1. Install Python**

Download and install Python from the official Python website.

**2. Install dependencies**

```bash
pip install mediapipe opencv-python pynput numpy
```

**3. Start the application**

```bash
python steering_wheel.py
```

**4. Camera not detected?**

Open `steering_wheel.py` and try changing:

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

> **Windows Camera Permission:** If Windows asks whether Python can access your camera, select **Allow**.

---

## 🍎 macOS Setup

This project was originally built and tested on **macOS with an Apple M2**.

macOS requires camera permission for the application running Python.

Go to:

**System Settings → Privacy & Security → Camera**

Enable camera access for:

* Terminal
* Python
* Your Python launcher, if applicable

Then run the project again.

---

## 🎛️ Configuration

Several settings can be adjusted at the top of `steering_wheel.py`.

| Setting              | Default | Purpose                                                    |
| -------------------- | ------: | ---------------------------------------------------------- |
| `CAMERA_INDEX`       |     `0` | Selects the webcam                                         |
| `DEAD_ZONE_DEG`      |    `12` | Ignores small steering movements near the center           |
| `FLIP_CAMERA`        |  `True` | Mirrors the webcam feed                                    |
| `GRACE_FRAMES`       |     `8` | Frames to wait before releasing keys when hands disappear  |
| `OPEN_FINGER_THRESH` |     `3` | Number of extended fingers required to detect an open hand |

### Example

```python
CAMERA_INDEX = 0
DEAD_ZONE_DEG = 12
FLIP_CAMERA = True
GRACE_FRAMES = 8
OPEN_FINGER_THRESH = 3
```

---

## 🔧 Troubleshooting

### Camera doesn't open

Try changing:

```python
CAMERA_INDEX = 0
```

to:

```python
CAMERA_INDEX = 1
```

or:

```python
CAMERA_INDEX = 2
```

---

### Steering direction is reversed

Try changing:

```python
FLIP_CAMERA = True
```

to:

```python
FLIP_CAMERA = False
```

---

### Keys remain pressed after removing your hands

The system waits for approximately **8 frames** before releasing the keyboard inputs.

Make sure your hands are completely outside the camera frame.

---

### Brake doesn't activate

Make sure your hands are clearly open and that at least **3 fingers are extended**.

---

### Brake activates too easily

Increase:

```python
OPEN_FINGER_THRESH = 4
```

This makes the open-hand detection more restrictive.

---

### Low FPS or lag

Try:

* Reducing the webcam resolution
* Closing unnecessary applications
* Using a better-lit environment
* Using a webcam with a higher frame rate

---

## 🎮 Compatible Games

The project works with games that support **keyboard arrow-key controls**.

Examples include:

* 🦖 Google Chrome Dinosaur Game
* 🏎️ Trackmania
* 🚗 TORCS
* 🏁 Hill Climb Racing (browser)
* 🎮 Other PC/browser racing games using arrow keys

---

## 💡 Key Features

* ✋ Hands-free car control
* 📷 Real-time webcam input
* 🧠 MediaPipe hand tracking
* 🎮 Keyboard-based game control
* ↔️ Gesture-based steering
* ⚡ Real-time response
* 🛑 Gesture-based braking
* 🚗 Works with multiple arrow-key-based games
* 🔧 Configurable detection parameters
* 💻 Windows and macOS support

---

## 🔮 Possible Future Improvements

Some possible extensions for the project include:

* Multiple gesture profiles
* Customizable controls
* Speed estimation
* More advanced hand gestures
* Voice commands
* Game-specific control profiles
* Mobile/web-based control interface
* AI-powered gesture classification

---

## 📁 Project Structure

```text
hand-gesture-car-control/
│
├── steering_wheel.py
├── hand_racing_game.py
├── hand_crazygames_controller.py
├── requirements.txt
├── README.md
└── LICENSE
```

---

## 👨‍💻 Author

**B. Sri Harsha**

Built as an exploration of **Computer Vision, Human-Computer Interaction, and real-time gesture-based control**.

---

## ⭐ Support

If you find this project interesting, consider giving the repository a ⭐ on GitHub!

**Repository:**
https://github.com/Harsha0304-dev/hand-gesture-car-control
