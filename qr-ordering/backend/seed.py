"""Create the tables and load a sample menu.

    python seed.py            # create tables + sample data (skips if a menu exists)
    python seed.py --reset    # drop everything first (deletes all orders!)
"""

import sys

from sqlalchemy import select

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Category, DiningTable, ItemOption, MenuItem
from app.qr import table_order_url

MENU = {
    "Burgers": [
        ("BBQ Chicken Burger", "Chicken, cheese, tomato, lettuce, onion and mayo on a sesame bun.", 1600),
        ("Chilli Beef Burger", "Beef, cheese, tomato, lettuce, onion, bacon and chilli mustard sauce.", 1600),
        ("Pork and Bacon Burger", "Pork patty, bacon, lettuce and special sauce.", 1700),
    ],
    "Sides": [
        ("Chips", "Crispy chips with chicken salt.", 600),
        ("Onion Rings", "Beer-battered onion rings.", 700),
    ],
    "Drinks": [
        ("Flat White", "Double shot.", 500),
        ("Soft Drink", "330ml can.", 400),
    ],
}

OPTIONS = {
    "BBQ Chicken Burger": [("Extras", "Extra cheese", 200), ("Extras", "Add bacon", 300)],
    "Chilli Beef Burger": [("Extras", "Extra cheese", 200), ("Extras", "Gluten-free bun", 150)],
    "Pork and Bacon Burger": [("Extras", "Extra cheese", 200)],
    "Flat White": [("Milk", "Oat milk", 80), ("Milk", "Soy milk", 80), ("Extras", "Extra shot", 60)],
}


def main() -> None:
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        if db.scalar(select(Category)) is not None:
            print("Menu already exists, skipping sample data.")
        else:
            for c_index, (category_name, items) in enumerate(MENU.items()):
                category = Category(name=category_name, sort_order=c_index)
                db.add(category)
                for i_index, (name, description, price) in enumerate(items):
                    item = MenuItem(
                        category=category,
                        name=name,
                        description=description,
                        price_cents=price,
                        sort_order=i_index,
                    )
                    db.add(item)
                    for o_index, (group, option_name, option_price) in enumerate(OPTIONS.get(name, [])):
                        db.add(
                            ItemOption(
                                item=item,
                                group_name=group,
                                name=option_name,
                                price_cents=option_price,
                                sort_order=o_index,
                            )
                        )
            for n in range(1, 6):
                db.add(DiningTable(name=f"Table {n}"))
            db.commit()
            print("Sample menu and 5 tables created.")

        frontend_url = get_settings().frontend_url
        for table in db.scalars(select(DiningTable)):
            print(f"  {table.name}: {table_order_url(frontend_url, table.qr_token)}")


if __name__ == "__main__":
    main()
