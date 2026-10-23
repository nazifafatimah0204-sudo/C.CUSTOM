"""Sample documents with deliberate mistakes, so you can test the app without any files."""

SAMPLE_DOCS = {
    "commercial_invoice": """COMMERCIAL INVOICE
Invoice No: INV-2026-0457        Date: 12 September 2026
Seller: Shenzhen BrightTech Co., Ltd, 88 Nanshan Road, Shenzhen, China
Buyer / Consignee: Al-Noor Electronics (Pvt) Ltd, 14 Mall Road, Lahore, Pakistan
Country of Origin: China
Payment Terms: 30 days after B/L date
Currency: USD

Item | Description                       | HS Code  | Qty  | Unit Price | Total
1    | Lithium-ion power banks 10000mAh  | 8507.60  | 500  | USD 8.50   | USD 4,250.00
2    | USB-C charging cables 1m          | 8544.42  | 2000 | USD 0.60   | USD 1,300.00

Total Invoice Value: USD 5,550.00
""",
    "packing_list": """PACKING LIST
Ref Invoice: INV-2026-0457        Date: 13 September 2026
Shipper: Shenzhen BrightTech Co., Ltd
Consignee: Al Noor Electronics Pvt Ltd, 14 Mall Road, Lahore, Pakistan
Packages: 45 cartons
Goods: Lithium-ion power banks 10000mAh - 500 pcs (25 cartons); USB-C charging cables 1m - 2000 pcs (20 cartons)
Gross Weight: 612 kg      Net Weight: 548 kg
Volume: 3.9 CBM
Marks: ANE/LHE/2026
""",
    "bill_of_lading": """BILL OF LADING
B/L No: SZXLHE260933        Shipped on board: 10 September 2026
Shipper: Shenzhen BrightTech Co., Ltd
Consignee: Al-Noor Trading Company, Karachi, Pakistan
Notify Party: Al-Noor Electronics (Pvt) Ltd, Lahore
Vessel / Voyage: MV Pacific Star / 026E
Port of Loading: Shenzhen, China      Port of Discharge: Karachi, Pakistan
Container: MSKU1234567 (1x20GP)   Seal: CN88231
Packages: 42 cartons
Description of goods: Electronic accessories
Gross Weight: 689 kg
Freight: Collect
""",
}
