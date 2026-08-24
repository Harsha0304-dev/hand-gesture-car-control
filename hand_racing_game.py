import math
import time
import random

import cv2
import mediapipe as mp
import numpy as np
import pygame


# ============================================================
# HAND GESTURE RACING GAME
# ============================================================
#
# Controls:
#
#   Both hands horizontal       -> straight
#   Tilt both hands LEFT        -> steer left
#   Tilt both hands RIGHT       -> steer right
#
#   Both fists                  -> ACCELERATE
#   Both open hands             -> BRAKE
#   One fist + one open hand    -> COAST
#
#   C                           -> show/hide camera preview
#   Q / ESC                     -> quit
#
# No keyboard controller is used for driving.
# Webcam + MediaPipe directly control the car.
# ============================================================


# ============================================================
# DISPLAY
# ============================================================

WIDTH = 1280
HEIGHT = 720
FPS = 60

WINDOW_TITLE = "Hand Gesture Racing"


# ============================================================
# CAMERA
# ============================================================

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


# ============================================================
# HAND STEERING SENSITIVITY
# ============================================================

# Small hand movements inside this angle are ignored.
DEAD_ZONE_DEG = 5.0

# At this angle steering reaches maximum.
MAX_STEER_DEG = 32.0

# Lower value = more sensitive around the center.
STEER_CURVE = 0.68

# Hand-angle smoothing.
ANGLE_SMOOTHING = 0.18

# Final steering smoothing.
STEERING_SMOOTHING = 0.28


# ============================================================
# HAND DETECTION
# ============================================================

OPEN_FINGER_THRESH = 3

MIN_DETECTION_CONF = 0.65
MIN_TRACKING_CONF = 0.55

MAX_NUM_HANDS = 2


# ============================================================
# GAME PHYSICS
# ============================================================

MAX_SPEED = 220.0

ACCELERATION = 105.0
BRAKE_POWER = 190.0
DRAG = 32.0

STEERING_RATE = 1.85

OFFROAD_GRIP = 0.55


# ============================================================
# ROAD
# ============================================================

ROAD_WIDTH_BOTTOM = 0.86
ROAD_WIDTH_TOP = 0.055

HORIZON = 0.39


# ============================================================
# RANDOM WORLD
# ============================================================

random.seed(7)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def lerp(a, b, amount):
    return a + (b - a) * amount


# ============================================================
# HAND OPEN/FIST DETECTION
# ============================================================

def is_open_hand(hand_landmarks):

    finger_tips = [
        8,
        12,
        16,
        20
    ]

    finger_pips = [
        6,
        10,
        14,
        18
    ]

    extended = 0

    for tip, pip in zip(
        finger_tips,
        finger_pips
    ):

        if (
            hand_landmarks.landmark[tip].y
            <
            hand_landmarks.landmark[pip].y
        ):

            extended += 1

    return extended >= OPEN_FINGER_THRESH


# ============================================================
# HAND CONTROLLER
# ============================================================

class HandController:

    def __init__(self):

        self.angle = 0.0

        self.steering = 0.0

        self.left_open = False
        self.right_open = False

        self.visible = False

        self.last_seen = time.time()


    # --------------------------------------------------------
    # UPDATE STEERING
    # --------------------------------------------------------

    def update(self, left_wrist, right_wrist):

        dx = (
            right_wrist[0]
            -
            left_wrist[0]
        )

        dy = (
            right_wrist[1]
            -
            left_wrist[1]
        )

        raw_angle = math.degrees(
            math.atan2(dy, dx)
        )

        self.angle = lerp(
            self.angle,
            raw_angle,
            ANGLE_SMOOTHING
        )

        # ----------------------------------------------------
        # DEAD ZONE
        # ----------------------------------------------------

        if abs(self.angle) <= DEAD_ZONE_DEG:

            target_steering = 0.0

        else:

            magnitude = (
                abs(self.angle)
                -
                DEAD_ZONE_DEG
            ) / (
                MAX_STEER_DEG
                -
                DEAD_ZONE_DEG
            )

            magnitude = clamp(
                magnitude,
                0.0,
                1.0
            )

            # Non-linear sensitivity.
            magnitude = (
                magnitude
                **
                STEER_CURVE
            )

            if self.angle > 0:

                target_steering = magnitude

            else:

                target_steering = -magnitude

        # ----------------------------------------------------
        # SMOOTH STEERING
        # ----------------------------------------------------

        self.steering = lerp(
            self.steering,
            target_steering,
            STEERING_SMOOTHING
        )

        self.visible = True

        self.last_seen = time.time()


    # --------------------------------------------------------
    # THROTTLE / BRAKE
    # --------------------------------------------------------

    def throttle(self):

        # Safety timeout.
        if (
            not self.visible
            or
            time.time() - self.last_seen > 0.35
        ):

            return (
                0.0,
                0.0,
                "SHOW BOTH HANDS"
            )

        both_fist = (
            not self.left_open
            and
            not self.right_open
        )

        both_open = (
            self.left_open
            and
            self.right_open
        )

        # BOTH FISTS
        if both_fist:

            return (
                1.0,
                0.0,
                "ACCELERATE"
            )

        # BOTH OPEN
        if both_open:

            return (
                0.0,
                1.0,
                "BRAKE"
            )

        # MIXED
        return (
            0.0,
            0.0,
            "COAST"
        )


    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    def reset(self):

        self.visible = False

        self.steering = 0.0

        self.angle = 0.0

        self.left_open = False
        self.right_open = False


# ============================================================
# ROAD OBJECT
# ============================================================

class RoadObject:

    def __init__(
        self,
        kind,
        z,
        side,
        offset
    ):

        self.kind = kind

        self.z = z

        self.side = side

        self.offset = offset

        self.seed = random.random() * 1000


# ============================================================
# PLAYER CAR
# ============================================================

class Racer:

    def __init__(self):

        self.speed = 0.0

        self.distance = 0.0

        self.lane = 0.0

        self.steer_visual = 0.0

        self.lap = 1

        self.lap_distance = 0.0

        self.best_lap = None

        self.lap_start = time.time()

        self.crash_timer = 0.0


    # --------------------------------------------------------
    # UPDATE CAR
    # --------------------------------------------------------

    def update(
        self,
        controller,
        dt
    ):

        accel, brake, mode = (
            controller.throttle()
        )

        # ----------------------------------------------------
        # SPEED
        # ----------------------------------------------------

        if accel:

            self.speed += (
                ACCELERATION
                *
                dt
            )

        elif brake:

            self.speed -= (
                BRAKE_POWER
                *
                dt
            )

        else:

            self.speed -= (
                DRAG
                *
                dt
            )

        self.speed = clamp(
            self.speed,
            0.0,
            MAX_SPEED
        )


        # ----------------------------------------------------
        # STEERING
        # ----------------------------------------------------

        if abs(self.lane) > 0.88:

            grip = OFFROAD_GRIP

        else:

            grip = 1.0


        steering_speed = (
            0.45
            +
            self.speed / MAX_SPEED
        )


        self.lane += (
            controller.steering
            *
            STEERING_RATE
            *
            dt
            *
            steering_speed
            *
            grip
        )


        self.lane = clamp(
            self.lane,
            -1.18,
            1.18
        )


        self.steer_visual = lerp(
            self.steer_visual,
            controller.steering,
            0.16
        )


        # ----------------------------------------------------
        # DISTANCE
        # ----------------------------------------------------

        self.distance += (
            self.speed
            *
            dt
        )

        self.lap_distance += (
            self.speed
            *
            dt
        )


        # ----------------------------------------------------
        # LAP
        # ----------------------------------------------------

        lap_length = 2500.0

        if self.lap_distance >= lap_length:

            elapsed = (
                time.time()
                -
                self.lap_start
            )

            if (
                self.best_lap is None
                or
                elapsed < self.best_lap
            ):

                self.best_lap = elapsed

            self.lap += 1

            self.lap_distance -= (
                lap_length
            )

            self.lap_start = time.time()


        # ----------------------------------------------------
        # CRASH TIMER
        # ----------------------------------------------------

        if self.crash_timer > 0:

            self.crash_timer -= dt


        # ----------------------------------------------------
        # OFFROAD
        # ----------------------------------------------------

        if (
            abs(self.lane) > 1.02
            and
            self.speed > 90
        ):

            self.speed *= 0.965

            self.crash_timer = max(
                self.crash_timer,
                0.15
            )


# ============================================================
# MAIN GAME
# ============================================================

class RacingGame:

    def __init__(self):

        # ----------------------------------------------------
        # PYGAME
        # ----------------------------------------------------

        pygame.init()

        pygame.display.set_caption(
            WINDOW_TITLE
        )

        self.screen = pygame.display.set_mode(
            (
                WIDTH,
                HEIGHT
            ),
            pygame.DOUBLEBUF
        )

        self.clock = pygame.time.Clock()

        # ----------------------------------------------------
        # FONTS
        # ----------------------------------------------------

        self.font = pygame.font.SysFont(
            "Segoe UI",
            22
        )

        self.bigfont = pygame.font.SysFont(
            "Segoe UI",
            42,
            bold=True
        )

        self.smallfont = pygame.font.SysFont(
            "Segoe UI",
            16
        )

        # ----------------------------------------------------
        # GAME STATE
        # ----------------------------------------------------

        self.running = True

        self.controller = (
            HandController()
        )

        self.car = Racer()

        # ----------------------------------------------------
        # ROAD OBJECTS
        # ----------------------------------------------------

        self.objects = []

        for i in range(85):

            z = i / 85.0

            kind = random.choice(
                [
                    "tree",
                    "tree",
                    "tree",
                    "sign",
                    "lamp"
                ]
            )

            side = random.choice(
                [-1, 1]
            )

            offset = random.uniform(
                1.05,
                1.55
            )

            self.objects.append(
                RoadObject(
                    kind,
                    z,
                    side,
                    offset
                )
            )


        # ----------------------------------------------------
        # MEDIAPIPE
        # ----------------------------------------------------

        self.hands = (
            mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=MAX_NUM_HANDS,
                model_complexity=0,
                min_detection_confidence=MIN_DETECTION_CONF,
                min_tracking_confidence=MIN_TRACKING_CONF,
            )
        )

        self.mp_drawing = (
            mp.solutions.drawing_utils
        )


        # ----------------------------------------------------
        # CAMERA
        # ----------------------------------------------------

        self.cap = cv2.VideoCapture(
            CAMERA_INDEX,
            cv2.CAP_DSHOW
        )

        if not self.cap.isOpened():

            self.cap = cv2.VideoCapture(
                CAMERA_INDEX
            )


        if not self.cap.isOpened():

            raise RuntimeError(
                "Cannot open camera index 0."
            )


        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            CAMERA_WIDTH
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            CAMERA_HEIGHT
        )


        # ----------------------------------------------------
        # CAMERA PREVIEW
        # ----------------------------------------------------

        self.camera_surface = None

        self.show_camera = False


    # ========================================================
    # ROAD PROJECTION
    # ========================================================

    def project(
        self,
        z,
        road_center_shift=0.0
    ):

        z = clamp(
            z,
            0.0,
            1.0
        )

        y = int(
            HEIGHT * HORIZON
            +
            (
                HEIGHT * 0.60
                *
                (
                    z ** 1.55
                )
            )
        )

        half_width = (
            WIDTH
            *
            (
                ROAD_WIDTH_TOP * 0.5
                +
                (
                    ROAD_WIDTH_BOTTOM
                    *
                    0.5
                    *
                    (
                        z ** 1.25
                    )
                )
            )
        )

        center = (
            WIDTH * 0.5
            +
            road_center_shift
            *
            WIDTH
            *
            0.10
            *
            (
                z ** 1.7
            )
        )

        return (
            center,
            half_width,
            y
        )


    # ========================================================
    # SKY
    # ========================================================

    def draw_sky(self):

        sky_bottom = int(
            HEIGHT * HORIZON
        )

        for y in range(
            sky_bottom + 1
        ):

            t = (
                y
                /
                max(
                    sky_bottom,
                    1
                )
            )

            color = (
                int(
                    38
                    +
                    80
                    *
                    (
                        1 - t
                    )
                ),
                int(
                    80
                    +
                    95
                    *
                    (
                        1 - t
                    )
                ),
                int(
                    120
                    +
                    100
                    *
                    (
                        1 - t
                    )
                )
            )

            pygame.draw.line(
                self.screen,
                color,
                (0, y),
                (WIDTH, y)
            )


        # ----------------------------------------------------
        # SUN
        # ----------------------------------------------------

        pygame.draw.circle(
            self.screen,
            (255, 235, 165),
            (
                WIDTH - 190,
                120
            ),
            55
        )

        pygame.draw.circle(
            self.screen,
            (255, 246, 205),
            (
                WIDTH - 190,
                120
            ),
            38
        )


        # ----------------------------------------------------
        # MOUNTAINS
        # ----------------------------------------------------

        points = [
            (
                0,
                sky_bottom
            )
        ]

        for x in range(
            0,
            WIDTH + 80,
            80
        ):

            peak = int(
                HEIGHT
                *
                (
                    0.27
                    +
                    0.09
                    *
                    math.sin(
                        x * 0.011
                    )
                    +
                    0.035
                    *
                    math.sin(
                        x * 0.031
                    )
                )
            )

            points.append(
                (
                    x,
                    peak
                )
            )

        points.extend(
            [
                (
                    WIDTH,
                    sky_bottom
                ),
                (
                    0,
                    sky_bottom
                )
            ]
        )

        pygame.draw.polygon(
            self.screen,
            (62, 75, 88),
            points
        )


        # ----------------------------------------------------
        # DISTANT FOREST
        # ----------------------------------------------------

        for x in range(
            0,
            WIDTH,
            18
        ):

            tree_height = (
                20
                +
                int(
                    12
                    *
                    math.sin(
                        x * 0.07
                    )
                )
            )

            y = sky_bottom

            pygame.draw.polygon(
                self.screen,
                (34, 67, 49),
                [
                    (
                        x,
                        y
                    ),
                    (
                        x + 9,
                        y - tree_height
                    ),
                    (
                        x + 18,
                        y
                    )
                ]
            )


    # ========================================================
    # ROAD
    # ========================================================

    def draw_road(self):

        horizon_y = int(
            HEIGHT * HORIZON
        )

        # Grass
        pygame.draw.rect(
            self.screen,
            (35, 91, 49),
            (
                0,
                horizon_y,
                WIDTH,
                HEIGHT
            )
        )


        # ----------------------------------------------------
        # ROAD SEGMENTS
        # ----------------------------------------------------

        for i in range(70):

            z0 = i / 70.0
            z1 = (i + 1) / 70.0

            curve0 = (
                0.22
                *
                math.sin(
                    self.car.distance
                    *
                    0.0007
                    +
                    z0 * 5.2
                )
                +
                0.08
                *
                math.sin(
                    z0 * 13
                )
            )

            curve1 = (
                0.22
                *
                math.sin(
                    self.car.distance
                    *
                    0.0007
                    +
                    z1 * 5.2
                )
                +
                0.08
                *
                math.sin(
                    z1 * 13
                )
            )

            c0, h0, y0 = (
                self.project(
                    z0,
                    curve0
                )
            )

            c1, h1, y1 = (
                self.project(
                    z1,
                    curve1
                )
            )


            # ------------------------------------------------
            # ROAD
            # ------------------------------------------------

            pygame.draw.polygon(
                self.screen,
                (45, 47, 50),
                [
                    (
                        c0 - h0,
                        y0
                    ),
                    (
                        c0 + h0,
                        y0
                    ),
                    (
                        c1 + h1,
                        y1
                    ),
                    (
                        c1 - h1,
                        y1
                    )
                ]
            )


            # ------------------------------------------------
            # ROAD EDGES
            # ------------------------------------------------

            edge_width = max(
                1,
                int(
                    1
                    +
                    4 * z1
                )
            )

            pygame.draw.line(
                self.screen,
                (225, 225, 220),
                (
                    c0 - h0,
                    y0
                ),
                (
                    c1 - h1,
                    y1
                ),
                edge_width
            )

            pygame.draw.line(
                self.screen,
                (225, 225, 220),
                (
                    c0 + h0,
                    y0
                ),
                (
                    c1 + h1,
                    y1
                ),
                edge_width
            )


            # ------------------------------------------------
            # CENTER LINE
            # ------------------------------------------------

            phase = int(
                (
                    self.car.distance
                    *
                    0.035
                    +
                    i
                )
                %
                12
            )

            if phase < 6:

                pygame.draw.line(
                    self.screen,
                    (240, 220, 160),
                    (
                        c0,
                        y0
                    ),
                    (
                        c1,
                        y1
                    ),
                    max(
                        1,
                        int(
                            1
                            +
                            5 * z1
                        )
                    )
                )


            # ------------------------------------------------
            # KERBS
            # ------------------------------------------------

            if i % 2 == 0:

                kerb_width = max(
                    2,
                    int(
                        2
                        +
                        7 * z1
                    )
                )

                pygame.draw.line(
                    self.screen,
                    (185, 45, 45),
                    (
                        c0 - h0,
                        y0
                    ),
                    (
                        c1 - h1,
                        y1
                    ),
                    kerb_width
                )

                pygame.draw.line(
                    self.screen,
                    (185, 45, 45),
                    (
                        c0 + h0,
                        y0
                    ),
                    (
                        c1 + h1,
                        y1
                    ),
                    kerb_width
                )


    # ========================================================
    # ROAD OBJECTS
    # ========================================================

    def draw_object(self, obj):

        relative_z = (
            obj.z
            +
            (
                self.car.distance
                *
                0.00042
            )
        ) % 1.0


        if relative_z < 0.05:
            return


        center, half, y = (
            self.project(
                relative_z
            )
        )

        x = int(
            center
            +
            obj.side
            *
            half
            *
            obj.offset
        )

        scale = (
            0.25
            +
            relative_z
            *
            1.35
        )


        # ----------------------------------------------------
        # TREE
        # ----------------------------------------------------

        if obj.kind == "tree":

            trunk_height = int(
                35 * scale
            )

            crown = max(
                3,
                int(
                    27 * scale
                )
            )

            trunk_width = max(
                2,
                int(
                    8 * scale
                )
            )

            pygame.draw.rect(
                self.screen,
                (74, 45, 27),
                (
                    x
                    -
                    max(
                        1,
                        int(
                            4 * scale
                        )
                    ),
                    y - trunk_height,
                    trunk_width,
                    trunk_height
                )
            )

            pygame.draw.circle(
                self.screen,
                (25, 88, 42),
                (
                    x,
                    y
                    -
                    trunk_height
                    -
                    crown // 2
                ),
                crown
            )

            pygame.draw.circle(
                self.screen,
                (31, 111, 48),
                (
                    x - crown // 2,
                    y - trunk_height
                ),
                max(
                    2,
                    crown // 2
                )
            )

            pygame.draw.circle(
                self.screen,
                (21, 76, 35),
                (
                    x + crown // 2,
                    y - trunk_height
                ),
                max(
                    2,
                    crown // 2
                )
            )


        # ----------------------------------------------------
        # SIGN
        # ----------------------------------------------------

        elif obj.kind == "sign":

            height = max(
                5,
                int(
                    42 * scale
                )
            )

            pole_width = max(
                1,
                int(
                    2 * scale
                )
            )

            pygame.draw.line(
                self.screen,
                (80, 80, 80),
                (
                    x,
                    y
                ),
                (
                    x,
                    y - height
                ),
                pole_width
            )

            pygame.draw.rect(
                self.screen,
                (235, 220, 170),
                (
                    x
                    -
                    int(
                        14 * scale
                    ),
                    y
                    -
                    height
                    -
                    int(
                        12 * scale
                    ),
                    max(
                        3,
                        int(
                            28 * scale
                        )
                    ),
                    max(
                        3,
                        int(
                            24 * scale
                        )
                    )
                )
            )


        # ----------------------------------------------------
        # LAMP
        # ----------------------------------------------------

        else:

            height = max(
                6,
                int(
                    70 * scale
                )
            )

            pygame.draw.line(
                self.screen,
                (100, 100, 100),
                (
                    x,
                    y
                ),
                (
                    x,
                    y - height
                ),
                max(
                    1,
                    int(
                        3 * scale
                    )
                )
            )

            pygame.draw.circle(
                self.screen,
                (245, 240, 185),
                (
                    x,
                    y - height
                ),
                max(
                    2,
                    int(
                        5 * scale
                    )
                )
            )


    # ========================================================
    # PLAYER CAR
    # ========================================================

    def draw_car(self):

        cx = (
            WIDTH // 2
            +
            int(
                self.car.lane
                *
                WIDTH
                *
                0.23
            )
        )

        cy = HEIGHT - 88

        car_width = 160
        car_height = 78


        # ----------------------------------------------------
        # SHADOW
        # ----------------------------------------------------

        pygame.draw.ellipse(
            self.screen,
            (15, 18, 18),
            (
                cx
                -
                car_width // 2
                +
                8,
                cy + 28,
                car_width - 16,
                30
            )
        )


        # ----------------------------------------------------
        # WHEELS
        # ----------------------------------------------------

        for wheel_x in (
            cx - 67,
            cx + 67
        ):

            # Correct Pygame API:
            # pygame.draw.rect(..., border_radius=...)

            pygame.draw.rect(
                self.screen,
                (18, 18, 20),
                (
                    wheel_x - 13,
                    cy - 5,
                    26,
                    54
                ),
                border_radius=7
            )

            pygame.draw.circle(
                self.screen,
                (115, 115, 120),
                (
                    wheel_x,
                    cy + 22
                ),
                7
            )


        # ----------------------------------------------------
        # CAR BODY
        # ----------------------------------------------------

        body = [
            (
                cx - 76,
                cy + 25
            ),
            (
                cx - 61,
                cy - 8
            ),
            (
                cx - 39,
                cy - 38
            ),
            (
                cx + 38,
                cy - 38
            ),
            (
                cx + 61,
                cy - 8
            ),
            (
                cx + 76,
                cy + 25
            ),
            (
                cx + 57,
                cy + 42
            ),
            (
                cx - 57,
                cy + 42
            )
        ]


        pygame.draw.polygon(
            self.screen,
            (180, 30, 35),
            body
        )


        # ----------------------------------------------------
        # ROOF
        # ----------------------------------------------------

        pygame.draw.polygon(
            self.screen,
            (225, 45, 48),
            [
                (
                    cx - 48,
                    cy - 10
                ),
                (
                    cx - 32,
                    cy - 31
                ),
                (
                    cx + 32,
                    cy - 31
                ),
                (
                    cx + 48,
                    cy - 10
                )
            ]
        )


        # ----------------------------------------------------
        # WINDSHIELD
        # ----------------------------------------------------

        pygame.draw.polygon(
            self.screen,
            (32, 48, 60),
            [
                (
                    cx - 28,
                    cy - 29
                ),
                (
                    cx - 20,
                    cy - 8
                ),
                (
                    cx + 20,
                    cy - 8
                ),
                (
                    cx + 28,
                    cy - 29
                )
            ]
        )


        # ----------------------------------------------------
        # HOOD HIGHLIGHT
        # ----------------------------------------------------

        pygame.draw.line(
            self.screen,
            (255, 110, 105),
            (
                cx - 55,
                cy + 7
            ),
            (
                cx + 55,
                cy + 7
            ),
            3
        )


        # ----------------------------------------------------
        # HEADLIGHTS
        # ----------------------------------------------------

        pygame.draw.ellipse(
            self.screen,
            (255, 220, 170),
            (
                cx - 55,
                cy + 7,
                24,
                12
            )
        )

        pygame.draw.ellipse(
            self.screen,
            (255, 220, 170),
            (
                cx + 31,
                cy + 7,
                24,
                12
            )
        )


        # ----------------------------------------------------
        # STEERING INDICATOR
        # ----------------------------------------------------

        if abs(
            self.car.steer_visual
        ) > 0.04:

            if self.car.steer_visual < 0:
                text = "LEFT"
            else:
                text = "RIGHT"

            surface = (
                self.smallfont.render(
                    text,
                    True,
                    (245, 245, 245)
                )
            )

            self.screen.blit(
                surface,
                (
                    cx
                    -
                    surface.get_width() // 2,
                    cy + 43
                )
            )


    # ========================================================
    # HUD
    # ========================================================

    def draw_hud(
        self,
        fps,
        mode
    ):

        panel = pygame.Surface(
            (
                430,
                135
            ),
            pygame.SRCALPHA
        )

        panel.fill(
            (
                8,
                12,
                18,
                190
            )
        )

        self.screen.blit(
            panel,
            (
                20,
                20
            )
        )


        # ----------------------------------------------------
        # SPEED
        # ----------------------------------------------------

        speed = int(
            self.car.speed
        )

        speed_text = (
            self.bigfont.render(
                f"{speed:03d} km/h",
                True,
                (235, 240, 245)
            )
        )

        self.screen.blit(
            speed_text,
            (
                35,
                29
            )
        )


        # ----------------------------------------------------
        # LAP
        # ----------------------------------------------------

        lap_text = (
            self.font.render(
                f"LAP {self.car.lap}",
                True,
                (230, 210, 150)
            )
        )

        self.screen.blit(
            lap_text,
            (
                35,
                88
            )
        )


        # ----------------------------------------------------
        # STEERING
        # ----------------------------------------------------

        steer_text = (
            self.font.render(
                f"STEER {self.car.steer_visual:+.0%}",
                True,
                (170, 220, 255)
            )
        )

        self.screen.blit(
            steer_text,
            (
                130,
                88
            )
        )


        # ----------------------------------------------------
        # MODE
        # ----------------------------------------------------

        mode_text = (
            self.font.render(
                mode,
                True,
                (120, 240, 160)
            )
        )

        self.screen.blit(
            mode_text,
            (
                285,
                88
            )
        )


        # ----------------------------------------------------
        # HAND STATUS
        # ----------------------------------------------------

        hands_connected = (
            self.controller.visible
            and
            time.time()
            -
            self.controller.last_seen
            <
            0.35
        )

        if hands_connected:

            status = (
                "HANDS CONNECTED"
            )

            status_color = (
                80,
                235,
                120
            )

        else:

            status = (
                "SHOW BOTH HANDS"
            )

            status_color = (
                245,
                90,
                70
            )


        status_surface = (
            self.smallfont.render(
                status,
                True,
                status_color
            )
        )

        self.screen.blit(
            status_surface,
            (
                WIDTH - 210,
                25
            )
        )


        # ----------------------------------------------------
        # CAMERA PREVIEW
        # ----------------------------------------------------

        if (
            self.show_camera
            and
            self.camera_surface is not None
        ):

            self.screen.blit(
                self.camera_surface,
                (
                    WIDTH - 270,
                    HEIGHT - 205
                )
            )


        # ----------------------------------------------------
        # CONTROLS
        # ----------------------------------------------------

        hint = (
            self.smallfont.render(
                "Both fists: ACCEL   |   Both open: BRAKE   |   C: camera   |   Q/ESC: quit",
                True,
                (220, 225, 230)
            )
        )

        self.screen.blit(
            hint,
            (
                WIDTH // 2
                -
                hint.get_width() // 2,
                HEIGHT - 28
            )
        )


        # ----------------------------------------------------
        # FPS
        # ----------------------------------------------------

        fps_text = (
            self.smallfont.render(
                f"FPS {fps:.0f}",
                True,
                (190, 195, 200)
            )
        )

        self.screen.blit(
            fps_text,
            (
                WIDTH - 75,
                HEIGHT - 28
            )
        )


    # ========================================================
    # CAMERA / MEDIAPIPE
    # ========================================================

    def process_camera(self):

        ret, frame = (
            self.cap.read()
        )

        if not ret:

            return


        # Mirror camera.
        frame = cv2.flip(
            frame,
            1
        )


        # Convert BGR -> RGB.
        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        results = (
            self.hands.process(
                rgb
            )
        )


        hand_data = {}


        # ----------------------------------------------------
        # PROCESS HANDS
        # ----------------------------------------------------

        if (
            results.multi_hand_landmarks
            and
            results.multi_handedness
        ):

            for (
                landmarks,
                handedness
            ) in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):

                label = (
                    handedness
                    .classification[0]
                    .label
                )

                wrist = (
                    landmarks.landmark[0]
                )


                opened = (
                    is_open_hand(
                        landmarks
                    )
                )


                hand_data[label] = (
                    wrist.x,
                    wrist.y,
                    opened
                )


                # Draw landmarks
                # only when camera preview
                # is enabled.

                if self.show_camera:

                    self.mp_drawing.draw_landmarks(
                        frame,
                        landmarks,
                        mp.solutions.hands.HAND_CONNECTIONS
                    )


        # ----------------------------------------------------
        # TWO HANDS
        # ----------------------------------------------------

        if (
            "Left" in hand_data
            and
            "Right" in hand_data
        ):

            (
                left_x,
                left_y,
                left_open
            ) = hand_data["Left"]


            (
                right_x,
                right_y,
                right_open
            ) = hand_data["Right"]


            self.controller.left_open = (
                left_open
            )

            self.controller.right_open = (
                right_open
            )


            self.controller.update(
                (
                    left_x,
                    left_y
                ),
                (
                    right_x,
                    right_y
                )
            )


        else:

            # Safety timeout.
            if (
                time.time()
                -
                self.controller.last_seen
                >
                0.35
            ):

                self.controller.reset()


        # ----------------------------------------------------
        # CAMERA PREVIEW
        # ----------------------------------------------------

        if self.show_camera:

            small = cv2.resize(
                frame,
                (
                    250,
                    188
                )
            )

            small = cv2.cvtColor(
                small,
                cv2.COLOR_BGR2RGB
            )


            self.camera_surface = (
                pygame.surfarray.make_surface(
                    np.transpose(
                        small,
                        (
                            1,
                            0,
                            2
                        )
                    )
                )
            )


    # ========================================================
    # DRAW WORLD
    # ========================================================

    def draw(self):

        self.draw_sky()

        self.draw_road()


        # Draw far objects first.
        for obj in sorted(
            self.objects,
            key=lambda item: item.z
        ):

            self.draw_object(
                obj
            )


        self.draw_car()


    # ========================================================
    # GAME LOOP
    # ========================================================

    def run(self):

        previous_time = (
            time.time()
        )


        while self.running:

            current_time = (
                time.time()
            )


            dt = min(
                current_time
                -
                previous_time,
                0.05
            )


            previous_time = (
                current_time
            )


            # ------------------------------------------------
            # EVENTS
            # ------------------------------------------------

            for event in (
                pygame.event.get()
            ):

                if (
                    event.type
                    ==
                    pygame.QUIT
                ):

                    self.running = False


                elif (
                    event.type
                    ==
                    pygame.KEYDOWN
                ):

                    # Emergency quit.
                    if event.key in (
                        pygame.K_ESCAPE,
                        pygame.K_q
                    ):

                        self.running = False


                    # Camera preview.
                    elif (
                        event.key
                        ==
                        pygame.K_c
                    ):

                        self.show_camera = (
                            not self.show_camera
                        )


            # ------------------------------------------------
            # HAND TRACKING
            # ------------------------------------------------

            self.process_camera()


            # ------------------------------------------------
            # CAR PHYSICS
            # ------------------------------------------------

            self.car.update(
                self.controller,
                dt
            )


            # ------------------------------------------------
            # DRAW
            # ------------------------------------------------

            self.draw()


            fps = (
                self.clock.get_fps()
            )


            _, _, mode = (
                self.controller.throttle()
            )


            self.draw_hud(
                fps,
                mode
            )


            pygame.display.flip()


            self.clock.tick(
                FPS
            )


        self.shutdown()


    # ========================================================
    # CLEAN SHUTDOWN
    # ========================================================

    def shutdown(self):

        self.controller.reset()

        try:
            self.hands.close()
        except Exception:
            pass

        try:
            self.cap.release()
        except Exception:
            pass

        pygame.quit()


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        print("=" * 60)
        print("      HAND GESTURE RACING GAME")
        print("=" * 60)
        print()
        print("Starting camera...")
        print()
        print("Controls:")
        print("  Tilt hands LEFT/RIGHT = steering")
        print("  Both fists             = accelerate")
        print("  Both open hands        = brake")
        print("  Mixed hands            = coast")
        print("  C                      = camera preview")
        print("  Q / ESC                = quit")
        print()
        print("=" * 60)


        game = RacingGame()

        print()
        print("[OK] Camera connected.")
        print("[OK] MediaPipe initialized.")
        print("[OK] Racing game started.")
        print()


        game.run()


    except Exception as error:

        print()
        print("=" * 60)
        print("[ERROR]")
        print(error)
        print("=" * 60)
        print()

        print(
            "If pygame is missing, run:"
        )

        print(
            "python -m pip install pygame"
        )

        print()

        print(
            "If the camera cannot be opened,"
        )

        print(
            "check Windows Camera permissions."
        )


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":

    main()