from mongoengine import Document, StringField, IntField, BooleanField, URLField, EnumField
from enum import Enum

class StarRating(Enum):
    ONE = "1 Star"
    TWO = "2 Stars"
    THREE = "3 Stars"
    FOUR = "4 Stars"
    FIVE = "5 Stars"

class Item(Document):
    name = StringField(required=True, max_length=255)
    category = StringField(required=True)
    price = IntField(required=True, min_value=0)
    
    offer = BooleanField(default=False)
    offer_price = IntField(min_value=0, null=True, blank=True)
    
    image_link = URLField(null=True, blank=True)
    description = StringField()
    review = EnumField(StarRating, default=StarRating.FIVE)

    meta = {
        'collection': 'items'
    }

    def save(self, *args, **kwargs):
        # Enforce conditional logic
        if self.offer and self.offer_price is None:
            raise ValueError("offer_price is required when offer is set to True.")
        if not self.offer:
            self.offer_price = None
        
        # FIXED: Call super().save() instead of super().__init__.save()
        return super(Item, self).save(*args, **kwargs)