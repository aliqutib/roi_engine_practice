# AI Marketing ROI Predictor
### A* Search + Hill Climbing

---

## How to Run (Step by Step)

### 1. Open folder in VS Code
```
File → Open Folder → select ROI_Project
```

### 2. Open Terminal
```
Terminal → New Terminal
```

### 3. Install dependency
```bash
pip install pymongo
```

### 4. Start MongoDB
Make sure MongoDB is running on your machine:
```bash
# Windows
net start MongoDB

# Mac
brew services start mongodb-community
```

### 5. Load dataset into MongoDB (ONCE only)
```bash
python db.py
```
You should see: `✅ 200000 records loaded into MongoDB`

### 6. Run the project
```bash
python main.py
```

---

## File Structure

```
ROI_Project/
├── main.py                         ← START HERE
├── A_star.py                       ← Finds best channel combination
├── hill_climb.py                   ← Splits budget optimally
├── channel_profile.py              ← ChannelProfile class + MongoDB query
├── search_node.py                  ← SearchNode used by A*
├── db.py                           ← MongoDB connection + data loader
├── marketing_campaign_dataset.csv  ← Dataset (200,000 records)
└── requirements.txt
```

---

## Change the Budget

Open `main.py` and change:
```python
MAX_BUDGET = 30000   # ← set your budget here
```

---

## How It Works

```
main.py
  │
  ├── Step 1 — A_star.py
  │     Reads channels from MongoDB
  │     Finds the best COMBINATION of channels within budget
  │     Uses heuristic: ROI per dollar spent
  │
  └── Step 2 — hill_climb.py
        Takes channels chosen by A*
        Finds optimal BUDGET SPLIT using Hill Climbing
        Uses random restarts to escape local optima
        Returns: % allocation per channel
```
