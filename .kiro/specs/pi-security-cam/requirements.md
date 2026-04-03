# Requirements Document

## Introduction

A Python-based security camera application that runs on a Raspberry Pi 4 (virtualized on ARM Virtual Hardware / Corellium, backed by AWS Graviton instances). The system captures video from a USB webcam, performs local AI inference using YOLOE (YOLO with Embeddings) to detect a specific target — a knight in armor — via text-prompted zero-shot detection. Detected knights are visually highlighted with bounding boxes on a web-based live view served from the Pi. A lightweight HTML5 test reporting dashboard runs on the developer's local machine. The system is deployed over-the-air via SSH from the Kiro development environment.

## Glossary

- **Detector**: The YOLOE-based component that performs text-prompted zero-shot object detection, identifying objects matching a natural language description (e.g., "knight in armor")
- **Frame_Pipeline**: The end-to-end processing chain from frame capture through detection, annotation, and streaming
- **Web_View**: A lightweight web server running on the Pi that serves an MJPEG stream of the annotated camera feed along with a description of the detection target
- **Test_Reporter**: An HTML5 application running on the developer's local machine that displays test results from the on-device test suite
- **Deployment_Agent**: The component responsible for transferring and running the application on the Raspberry Pi over SSH
- **Pi**: The Raspberry Pi 4 target device (virtualized on ARM Virtual Hardware / Corellium, backed by AWS Graviton)

## Requirements

### Requirement 1: Capture Video from USB Camera

**User Story:** As a security operator, I want the system to capture live video from a USB webcam connected to the Pi, so that the system has a continuous feed to analyze.

#### Acceptance Criteria

1. WHEN the application starts, THE Frame_Pipeline SHALL open the default USB camera device and begin capturing frames
2. WHILE the camera is active, THE Frame_Pipeline SHALL capture frames continuously, processing each frame through the Detector before capturing the next
3. IF the camera device is unavailable or disconnected, THEN THE Frame_Pipeline SHALL log an error and retry connection at 5-second intervals
4. WHEN a frame is captured, THE Frame_Pipeline SHALL pass it to the Detector for analysis

### Requirement 2: Detect Knight in Armor Using Text-Prompted Zero-Shot Detection

**User Story:** As a security operator, I want the system to detect a knight in armor in the camera feed using a natural language description, so that I can identify the target without custom model training.

#### Acceptance Criteria

1. WHEN a frame is received, THE Detector SHALL run YOLOE inference using the configured text prompt (default: "knight in armor") to identify matching objects
2. THE Detector SHALL return bounding box coordinates and confidence scores for each detection matching the text prompt
3. THE Detector SHALL discard detections with a confidence score below a configurable threshold (default 0.3)
4. WHEN the application starts, THE Detector SHALL load the YOLOE model in ONNX format for optimized inference on ARM

### Requirement 3: Annotate Frames with Bounding Boxes

**User Story:** As a security operator viewing the camera feed, I want to see bounding boxes drawn only around detected knights in armor, so that I can quickly identify them.

#### Acceptance Criteria

1. WHEN the Detector identifies an object matching the text prompt, THE Frame_Pipeline SHALL draw a bounding box around that object on the frame
2. THE Frame_Pipeline SHALL label the bounding box with the detection target name and the confidence score
3. THE Frame_Pipeline SHALL use a distinct color (bright green) for detection bounding boxes
4. WHEN no detections are found in a frame, THE Frame_Pipeline SHALL pass the frame through without any annotations

### Requirement 4: Serve Annotated Camera Feed via Web View

**User Story:** As a security operator, I want to view the live annotated camera feed through a web browser, so that I can monitor the camera remotely.

#### Acceptance Criteria

1. WHEN the application starts, THE Web_View SHALL start an HTTP server on a configurable port (default 8080)
2. THE Web_View SHALL serve an HTML page that displays the target description (e.g., "Looking for: Knight in Armor") and an inline live camera view
3. THE Web_View SHALL stream annotated frames as an MJPEG stream embedded in the HTML page
4. WHILE the camera feed is active, THE Web_View SHALL update the displayed frame each time a new annotated frame is available
5. IF no camera feed is available, THEN THE Web_View SHALL display a placeholder message indicating the camera is offline

### Requirement 5: Configure the Application

**User Story:** As a developer, I want to configure detection parameters and the target description without modifying code, so that I can adapt the system to different scenarios.

#### Acceptance Criteria

1. WHEN the application starts, THE Frame_Pipeline SHALL load configuration from a JSON file specified via command-line argument
2. THE Frame_Pipeline SHALL support configuration of: camera device index, detection confidence threshold, web server port, target description text prompt, and YOLOE model path
3. IF a configuration file is not provided, THEN THE Frame_Pipeline SHALL use default values for all parameters
4. WHEN a configuration file contains invalid values, THE Frame_Pipeline SHALL log a validation error and exit with a non-zero status code

### Requirement 6: Deploy Application to Pi Over SSH

**User Story:** As a developer, I want to deploy the application to the Raspberry Pi over SSH from my development machine, so that I can demonstrate real-time development with Kiro.

#### Acceptance Criteria

1. THE Deployment_Agent SHALL provide a deployment script that copies application files to the Pi via SCP using the SSH key at /Users/dwaltrsd/.ssh/id_ed25519
2. THE Deployment_Agent SHALL connect to the Pi using the username "pi" and a session-provided hostname and password
3. WHEN deployment is triggered, THE Deployment_Agent SHALL install required Python dependencies on the Pi if not already present
4. WHEN deployment completes, THE Deployment_Agent SHALL start the application on the Pi as a background process

### Requirement 7: Run Tests on Device and Report to Local Dashboard

**User Story:** As a developer, I want to run the test suite on the Pi and see results in an HTML5 dashboard on my local machine, so that I can verify correctness during the demo.

#### Acceptance Criteria

1. THE Test_Reporter SHALL provide an HTML5 single-page application that displays test results
2. WHEN tests are executed on the Pi, THE test suite SHALL output results in JSON format to a file
3. THE Deployment_Agent SHALL copy the test results file from the Pi to the local machine after test execution
4. WHEN the Test_Reporter loads, THE Test_Reporter SHALL parse the JSON results file and display pass/fail status for each test
5. THE Test_Reporter SHALL display test name, status, duration, and failure details for each test case

### Requirement 8: Host as a Cloneable GitHub Repository

**User Story:** As a developer or demo attendee, I want to clone the repository from GitHub and get started by simply providing SSH credentials, so that setup is minimal and self-contained.

#### Acceptance Criteria

1. THE repository SHALL contain all application code, test suite, test reporter, deployment scripts, and configuration templates in a single cloneable repository
2. THE repository SHALL include a README with clear setup instructions covering prerequisites, cloning, and credential configuration
3. THE repository SHALL use a `.env` file or equivalent mechanism for session-specific credentials (SSH host, password) that is listed in `.gitignore`
4. THE repository SHALL include a `.env.example` template file showing all required credential fields with placeholder values
5. WHEN a user clones the repository and fills in the `.env` file, THE Deployment_Agent SHALL use those credentials to connect to the Pi without further configuration

### Requirement 9: Serialize and Deserialize Configuration

**User Story:** As a developer, I want configuration data to be reliably serialized to and from JSON, so that data integrity is maintained across read/write cycles.

#### Acceptance Criteria

1. WHEN storing configuration to a file, THE Frame_Pipeline SHALL encode it as JSON
2. WHEN loading configuration from a file, THE Frame_Pipeline SHALL decode it from JSON into an equivalent in-memory object
3. FOR ALL valid configuration objects, serializing then deserializing SHALL produce an equivalent object (round-trip property)
