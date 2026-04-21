from algo import a_star
from db import db

def main():

    MAX_BUDGET = 15000

    best_channels, roi_acheived, budget_used = a_star(max_budget=MAX_BUDGET, db=db)

    print(f"\nFINAL ANSWER: Use {set(best_channels)}")
    print(f"Expected ROI: {roi_acheived * 100:.1f}%")

if __name__ == "__main__":
    main()