# Video-Surveillance-and-tracking-system using Facial Recognition
<p>Connect all CCTV cameras to this system to track someone's live location in a premise using facial recognition. It can be also used to maintain records of people entering a premise using their face instead of bio-metrics/cards/manual Entry. </p>
This system when used with national criminal database can track criminals and prevent mishaps 

---

## How to Run the App

A unified, modern dark-themed tracking dashboard is implemented in `app.py`.

### 1. Activate Virtual Environment
```bash
source .venv/bin/activate
```

### 2. Run the Dashboard
If you run into `pkg_resources` missing errors (due to new pip environments in Python 3.12/3.13), downgrade setuptools first:
```bash
pip install "setuptools<82"
```

Then launch the dashboard:
```bash
python3 app.py
```

### Features:
- **Live Stream Tab**: Displays webcam feed, overlays green/red recognition bounding boxes, and records tracking events in real-time with an optimized DB update engine.
- **Register Member Tab**: Dynamic enrollment of new profiles (Name, Roll No/ID) with image preview.
- **Database Records Tab**: Interactive table viewer of all database entries with searchable list and profile photo inspect card.
