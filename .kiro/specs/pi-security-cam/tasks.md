# Implementation Plan: Pi Security Cam

## Overview

Incremental implementation of a YOLOE-based security camera application for Raspberry Pi. Tasks build sequentially from core data models through detection, annotation, native OpenCV display, deployment scripts, and test reporting. Python with pytest + Hypothesis for testing.

## Tasks

- [x] 1. Set up project structure and configuration
  - [x] 1.1 Create project directory structure, `requirements.txt`, `.gitignore`, `.env.example`, and `README.md`
    - Create `src/` directory with `__init__.py`, `config.py`, `detector.py`, `annotator.py`, `pipeline.py`, `display.py`, `main.py`
    - Create `tests/` directory with `__init__.py`, `conftest.py`
    - Create `scripts/deploy.sh`, `scripts/test.sh`
    - Create `test-reporter/index.html`
    - Create `config.json` with default values
    - `requirements.txt`: ultralytics, opencv-python, pytest, hypothesis, pytest-json-report
    - `.env.example` with `PI_HOST`, `PI_PASSWORD`, `PI_SSH_KEY` placeholders
    - `.gitignore` with `.env`, `__pycache__`, `*.pyc`, `results.json`
    - `README.md` with setup instructions
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 1.2 Implement `AppConfig` dataclass with JSON serialization/deserialization and validation
    - Define `AppConfig` dataclass in `src/config.py` with fields: `camera_device`, `confidence_threshold`, `target_description`, `model_path`
    - Implement `from_json()`, `to_json()`, `to_dict()`, `from_dict()` methods
    - Implement validation: camera_device >= 0, 0 < confidence_threshold <= 1.0, non-empty target_description, non-empty model_path
    - Implement CLI argument parsing for config file path with defaults
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 9.1, 9.2, 9.3_

  - [ ]* 1.3 Write property tests for AppConfig
    - **Property 5: Configuration round-trip**
    - **Validates: Requirements 9.3**
    - **Property 6: Invalid configuration rejection**
    - **Validates: Requirements 5.4**

- [x] 2. Implement detection and annotation
  - [x] 2.1 Implement `YOLOEDetector` with text-prompted detection
    - Define `Detection` dataclass with `bbox`, `confidence`, `label` fields
    - Implement `YOLOEDetector.__init__()` to load YOLOE model and set text prompt
    - Implement `detect()` method that runs inference and returns filtered detections
    - Implement confidence threshold filtering
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.2 Write property test for confidence filtering
    - **Property 1: Confidence threshold filtering**
    - **Validates: Requirements 2.3**

  - [x] 2.3 Implement `FrameAnnotator` with bounding box drawing
    - Implement `annotate()` method using OpenCV `cv2.rectangle()` and `cv2.putText()`
    - Use bright green (0, 255, 0) for bounding boxes
    - Label format: "{target_description} {confidence:.0%}"
    - Return unmodified frame when detections list is empty
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 2.4 Write property tests for FrameAnnotator
    - **Property 2: Annotation completeness**
    - **Validates: Requirements 3.1, 3.2**
    - **Property 3: No-detection passthrough**
    - **Validates: Requirements 3.4**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement display window and frame pipeline
  - [x] 4.1 Implement `DisplayWindow` with native OpenCV display
    - Implement `DisplayWindow` class in `src/display.py`
    - Use `cv2.namedWindow` to create window titled "Pi Security Cam"
    - Implement `show_frame()` with `cv2.putText` for target description overlay (e.g., "Looking for: Knight in Armor") and `cv2.imshow`
    - Implement `show_offline()` for black placeholder frame with "Camera Offline" text
    - Implement `check_quit()` using `cv2.waitKey` for 'q' key exit
    - Implement `close()` to destroy the OpenCV window
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 4.2 Write property test for display window target description overlay
    - **Property 4: Display window shows target description**
    - **Validates: Requirements 4.2**

  - [x] 4.3 Implement `FramePipeline` orchestrator
    - Implement camera capture with OpenCV `VideoCapture`
    - Implement frame processing loop in main thread: capture → detect → annotate → display via `DisplayWindow.show_frame()`
    - Implement camera retry logic (5-second intervals on failure)
    - Call `DisplayWindow.show_offline()` when camera is unavailable
    - Check `DisplayWindow.check_quit()` each iteration for 'q' key exit
    - Wire together Detector, Annotator, and DisplayWindow
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 4.4 Implement `main.py` entry point
    - Parse CLI arguments for config file path
    - Load config (or use defaults)
    - Initialize DisplayWindow and FramePipeline
    - Run the pipeline's main loop directly (main thread, required by OpenCV GUI)
    - Handle graceful shutdown on SIGINT/SIGTERM, calling `DisplayWindow.close()`
    - _Requirements: 5.1, 5.3_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement deployment and test reporting
  - [x] 6.1 Implement `deploy.sh` deployment script
    - Load `.env` for PI_HOST, PI_PASSWORD, PI_SSH_KEY
    - SCP application files to `pi@$PI_HOST:~/pi-security-cam/`
    - SSH to install dependencies via `pip install -r requirements.txt`
    - SSH to start application as background process with `nohup`
    - Error handling for missing `.env`, SSH failures
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.5_

  - [x] 6.2 Implement `test.sh` test runner script
    - SSH into Pi and run `pytest --json-report --json-report-file=results.json`
    - SCP `results.json` back to `test-reporter/results.json`
    - _Requirements: 7.2, 7.3_

  - [x] 6.3 Implement Test Reporter HTML5 dashboard
    - Single-page HTML5 app that loads `results.json`
    - Render table with test name, status (pass/fail), duration, failure details
    - Color-code pass (green) / fail (red)
    - Handle missing or malformed results file gracefully
    - _Requirements: 7.1, 7.4, 7.5_

  - [ ]* 6.4 Write property test for test results parsing
    - **Property 7: Test results parsing completeness**
    - **Validates: Requirements 7.4, 7.5**

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- Tests requiring YOLOE model or camera hardware should be marked `@pytest.mark.integration`
