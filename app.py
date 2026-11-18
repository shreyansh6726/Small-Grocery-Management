import os
import tkinter as tk
from tkinter import messagebox, ttk

from dotenv import load_dotenv
from mongoengine import connect
from mongoengine.errors import NotUniqueError, OperationError, ValidationError
from mongoengine.queryset.visitor import Q

from models.items import Item, StarRating


load_dotenv()


class GroceryAdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Grocery Store Admin Panel")
        self.root.geometry("1280x720")
        self.root.minsize(1000, 600)

        self.selected_item_id = None
        self.configure_database()
        self.configure_styles()
        self.build_layout()
        self.refresh_items()

    def configure_database(self):
        database = os.getenv("MONGODB_DATABASE", "grocery_store")
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

        try:
            connection = connect(
                db=database,
                host=uri,
                serverSelectionTimeoutMS=5000,
            )
            connection.admin.command("ping")
        except Exception as exc:
            messagebox.showwarning(
                "Database Connection",
                f"Could not connect to MongoDB:\n{exc}\n\n"
                "Set MONGODB_URI and MONGODB_DATABASE in a .env file.",
            )

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground="#176b3a")
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground="#27352e")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground="white")

    def build_layout(self):
        self.root.configure(padx=16, pady=16)

        title = ttk.Label(self.root, text="Grocery Inventory", style="Title.TLabel")
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        form_frame = ttk.LabelFrame(self.root, text="Item Details", padding=14)
        form_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

        table_frame = ttk.Frame(self.root)
        table_frame.grid(row=1, column=1, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(1, weight=1)

        fields = [
            ("Name", "name"),
            ("Category", "category"),
            ("Price", "price"),
            ("Offer Price", "offer_price"),
            ("Image URL", "image_link"),
        ]
        self.entries = {}

        for index, (label_text, field_name) in enumerate(fields):
            ttk.Label(form_frame, text=label_text).grid(
                row=index, column=0, sticky="w", pady=5
            )
            entry = ttk.Entry(form_frame, width=34)
            entry.grid(row=index, column=1, sticky="ew", padx=(8, 0), pady=5)
            self.entries[field_name] = entry

        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Description").grid(
            row=len(fields), column=0, sticky="nw", pady=5
        )
        self.description_text = tk.Text(form_frame, width=34, height=5, wrap="word")
        self.description_text.grid(
            row=len(fields), column=1, sticky="ew", padx=(8, 0), pady=5
        )

        self.offer_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form_frame,
            text="Active offer",
            variable=self.offer_var,
            command=self.toggle_offer_price,
        ).grid(row=len(fields) + 1, column=0, columnspan=2, sticky="w", pady=6)

        rating_row = len(fields) + 2
        ttk.Label(form_frame, text="Rating").grid(
            row=rating_row, column=0, sticky="w", pady=5
        )
        self.rating_var = tk.StringVar(value=StarRating.FIVE.value)
        ttk.Combobox(
            form_frame,
            textvariable=self.rating_var,
            values=[rating.value for rating in StarRating],
            state="readonly",
            width=31,
        ).grid(row=rating_row, column=1, sticky="ew", padx=(8, 0), pady=5)

        button_row = rating_row + 1
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=button_row, column=0, columnspan=2, pady=(12, 0), sticky="ew")
        button_frame.columnconfigure((0, 1, 2), weight=1)

        self.add_button = ttk.Button(button_frame, text="Add", command=self.add_item)
        self.add_button.grid(row=0, column=0, padx=3, sticky="ew")

        self.update_button = ttk.Button(
            button_frame, text="Update", command=self.update_item, state="disabled"
        )
        self.update_button.grid(row=0, column=1, padx=3, sticky="ew")

        self.delete_button = ttk.Button(
            button_frame, text="Delete", command=self.delete_item, state="disabled"
        )
        self.delete_button.grid(row=0, column=2, padx=3, sticky="ew")

        ttk.Button(form_frame, text="Clear Form", command=self.clear_form).grid(
            row=button_row + 1, column=0, columnspan=2, pady=(8, 0), sticky="ew"
        )

        search_frame = ttk.Frame(table_frame)
        search_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(search_frame, text="Search").pack(side="left", padx=(0, 8))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_items())

        ttk.Button(search_frame, text="Refresh", command=self.refresh_items).pack(
            side="left", padx=(8, 0)
        )

        columns = (
            "name",
            "category",
            "price",
            "offer_price",
            "rating",
        )
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headings = {
            "name": ("Name", 180),
            "category": ("Category", 130),
            "price": ("Price", 90),
            "offer_price": ("Offer Price", 100),
            "rating": ("Rating", 100),
        }
        for column in columns:
            heading, width = headings[column]
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.load_selected_item)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            relief="sunken",
            padding=(6, 4),
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.toggle_offer_price()

    def toggle_offer_price(self):
        entry = self.entries["offer_price"]
        if self.offer_var.get():
            entry.configure(state="normal")
        else:
            entry.configure(state="disabled")
            entry.delete(0, "end")

    def clear_form(self):
        self.selected_item_id = None
        for entry in self.entries.values():
            entry.configure(state="normal")
            entry.delete(0, "end")
        self.description_text.delete("1.0", "end")
        self.offer_var.set(False)
        self.rating_var.set(StarRating.FIVE.value)
        self.toggle_offer_price()
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.add_button.configure(state="normal")
        self.update_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.status_var.set("Ready")

    def parse_form(self):
        name = self.entries["name"].get().strip()
        category = self.entries["category"].get().strip()
        price_text = self.entries["price"].get().strip()
        offer_price_text = self.entries["offer_price"].get().strip()
        image_link = self.entries["image_link"].get().strip() or None
        description = self.description_text.get("1.0", "end").strip()

        if not name or not category or not price_text:
            raise ValueError("Name, category, and price are required.")

        try:
            price = int(price_text)
        except ValueError as exc:
            raise ValueError("Price must be a whole number.") from exc
        if price < 0:
            raise ValueError("Price cannot be negative.")

        offer_price = None
        if self.offer_var.get():
            if not offer_price_text:
                raise ValueError("Offer price is required when an offer is active.")
            try:
                offer_price = int(offer_price_text)
            except ValueError as exc:
                raise ValueError("Offer price must be a whole number.") from exc
            if offer_price < 0:
                raise ValueError("Offer price cannot be negative.")

        rating = next(
            (rating for rating in StarRating if rating.value == self.rating_var.get()),
            StarRating.FIVE,
        )

        return {
            "name": name,
            "category": category,
            "price": price,
            "offer": self.offer_var.get(),
            "offer_price": offer_price,
            "image_link": image_link,
            "description": description,
            "review": rating,
        }

    def add_item(self):
        try:
            values = self.parse_form()
            Item(**values).save()
        except (ValueError, ValidationError, NotUniqueError, OperationError) as exc:
            messagebox.showerror("Could Not Add Item", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Could Not Add Item", f"Unexpected error:\n{exc}")
            return

        self.clear_form()
        self.refresh_items()
        self.status_var.set(f"Added {values['name']}")

    def update_item(self):
        if not self.selected_item_id:
            messagebox.showwarning("No Item Selected", "Select an item to update.")
            return

        try:
            values = self.parse_form()
            item = Item.objects(id=self.selected_item_id).first()
            if item is None:
                raise ValueError("The selected item no longer exists.")
            for field, value in values.items():
                setattr(item, field, value)
            item.save()
        except (ValueError, ValidationError, NotUniqueError, OperationError) as exc:
            messagebox.showerror("Could Not Update Item", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Could Not Update Item", f"Unexpected error:\n{exc}")
            return

        self.clear_form()
        self.refresh_items()
        self.status_var.set(f"Updated {values['name']}")

    def delete_item(self):
        if not self.selected_item_id:
            messagebox.showwarning("No Item Selected", "Select an item to delete.")
            return

        try:
            item = Item.objects(id=self.selected_item_id).first()
        except Exception as exc:
            messagebox.showerror("Could Not Find Item", str(exc))
            return
        if item is None:
            messagebox.showwarning("Item Not Found", "The selected item no longer exists.")
            self.refresh_items()
            return

        if not messagebox.askyesno(
            "Delete Item",
            f"Delete '{item.name}'? This action cannot be undone.",
        ):
            return

        try:
            item.delete()
        except Exception as exc:
            messagebox.showerror("Could Not Delete Item", str(exc))
            return

        self.clear_form()
        self.refresh_items()
        self.status_var.set(f"Deleted {item.name}")

    def refresh_items(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            query = self.search_var.get().strip()
            if query:
                items = Item.objects(
                    Q(name__icontains=query)
                    | Q(category__icontains=query)
                    | Q(description__icontains=query)
                ).order_by("name")
            else:
                items = Item.objects.order_by("name")

            for item in items:
                offer_price = str(item.offer_price) if item.offer_price is not None else "-"
                review = item.review.value if isinstance(item.review, StarRating) else str(item.review)
                self.tree.insert(
                    "",
                    "end",
                    iid=str(item.id),
                    values=(
                        item.name,
                        item.category,
                        item.price,
                        offer_price,
                        review,
                    ),
                )
            self.status_var.set(f"{items.count()} item(s)")
        except Exception as exc:
            self.status_var.set("Could not load items")
            messagebox.showerror("Could Not Load Items", str(exc))

    def load_selected_item(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        try:
            item = Item.objects(id=item_id).first()
        except Exception as exc:
            messagebox.showerror("Could Not Load Item", str(exc))
            return
        if item is None:
            self.refresh_items()
            return

        self.selected_item_id = item.id
        self.entries["name"].delete(0, "end")
        self.entries["name"].insert(0, item.name)
        self.entries["category"].delete(0, "end")
        self.entries["category"].insert(0, item.category)
        self.entries["price"].delete(0, "end")
        self.entries["price"].insert(0, str(item.price))
        self.entries["image_link"].delete(0, "end")
        self.entries["image_link"].insert(0, item.image_link or "")

        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", item.description or "")

        self.offer_var.set(item.offer)
        self.entries["offer_price"].configure(state="normal")
        self.entries["offer_price"].delete(0, "end")
        if item.offer_price is not None:
            self.entries["offer_price"].insert(0, str(item.offer_price))
        self.toggle_offer_price()

        self.rating_var.set(
            item.review.value if isinstance(item.review, StarRating) else StarRating.FIVE.value
        )
        self.add_button.configure(state="disabled")
        self.update_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        self.status_var.set(f"Selected {item.name}")


def main():
    root = tk.Tk()
    app = GroceryAdminApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
