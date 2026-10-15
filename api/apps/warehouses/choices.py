from django.utils.translation import gettext_lazy as _

COUNTY_CHOICES = [
    ('MOMBASA', _('Mombasa')),
    ('KWALE', _('Kwale')),
    ('KILIFI', _('Kilifi')),
    ('TANA_RIVER', _('Tana River')),
    ('LAMU', _('Lamu')),
    ('TAITA_TAVETA', _('Taita Taveta')),
    ('GARISSA', _('Garissa')),
    ('WAJIR', _('Wajir')),
    ('MANDERA', _('Mandera')),
    ('MARSABIT', _('Marsabit')),
    ('ISIOLO', _('Isiolo')),
    ('MERU', _('Meru')),
    ('THARAKA_NITHI', _('Tharaka Nithi')),
    ('EMBU', _('Embu')),
    ('KITUI', _('Kitui')),
    ('MACHAKOS', _('Machakos')),
    ('MAKUENI', _('Makueni')),
    ('NYANDARUA', _('Nyandarua')),
    ('NYERI', _('Nyeri')),
    ('KIRINYAGA', _('Kirinyaga')),
    ('MURANGA', _('Murang\'a')),
    ('KIAMBU', _('Kiambu')),
    ('TURKANA', _('Turkana')),
    ('WEST_POKOT', _('West Pokot')),
    ('SAMBURU', _('Samburu')),
    ('TRANS_NZOIA', _('Trans Nzoia')),
    ('UASIN_GISHU', _('Uasin Gishu')),
    ('ELGEYO_MARAKWET', _('Elgeyo Marakwet')),
    ('NANDI', _('Nandi')),
    ('BARINGO', _('Baringo')),
    ('LAIKIPIA', _('Laikipia')),
    ('NAKURU', _('Nakuru')),
    ('NAROK', _('Narok')),
    ('KAJIADO', _('Kajiado')),
    ('KERICHO', _('Kericho')),
    ('BOMET', _('Bomet')),
    ('KAKAMEGA', _('Kakamega')),
    ('VIHIGA', _('Vihiga')),
    ('BUNGOMA', _('Bungoma')),
    ('BUSIA', _('Busia')),
    ('SIAYA', _('Siaya')),
    ('KISUMU', _('Kisumu')),
    ('HOMA_BAY', _('Homa Bay')),
    ('MIGORI', _('Migori')),
    ('KISII', _('Kisii')),
    ('NYAMIRA', _('Nyamira')),
    ('NAIROBI', _('Nairobi')),
]

WAREHOUSE_TYPES = [
    ('DRY', _('Dry Goods')),
    ('COLD', _('Cold Storage')),
    ('FROZEN', _('Frozen Goods')),
    ('HAZARD', _('Hazardous Materials')),
]

BIN_TYPES = [
    ('SHELF', _('Shelf')),
    ('PALLET', _('Pallet')),
    ('BIN', _('Storage Bin')),
    ('ROOM', _('Storage Room')),
]

STOCK_TRANSFER_STATUS_CHOICES = [
    ('PENDING', _('Pending Approval')),
    ('APPROVED', _('Approved')),
    ('IN_TRANSIT', _('In Transit')),
    ('RECEIVED', _('Received')),
    ('VERIFIED', _('Verified')),
    ('CANCELLED', _('Cancelled')),
]

STOCK_TRANSFER_TYPES = [
    ('INTERNAL', _('Internal Transfer')),
    ('SUPPLIER', _('Supplier Delivery')),
    ('CUSTOMER', _('Customer Return')),
    ('DAMAGED', _('Damaged Goods')),
]