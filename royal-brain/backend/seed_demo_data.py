"""
Royal BrAIn™ Demo Data Seeding Script

Creates 4 complete royal houses with:
- Full genealogies (4 generations each)
- Relationships (parent-child, marriages)
- Source documents
- Families
- Timeline-validated data

Run: python seed_demo_data.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import date, datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.sources.models import Source
from app.persons.models import Person
from app.relationships.models import Relationship
from app.families.models import Family
from app.jurisdictions.models import Jurisdiction
from app.orders.models import Order


def seed_demo_orders_if_missing(db: Session, *, commit: bool = True) -> int:
    """Seed a small set of demo orders if none exist.

    This keeps the Orders Engine UI usable out-of-the-box. Safe to call repeatedly.
    """

    existing_orders = db.query(Order).count()
    if existing_orders > 0:
        return 0

    # Need at least one source to attach (OrderCreate requires >=1 source_ids; we mirror that intent).
    any_source = db.query(Source).order_by(Source.id.asc()).first()
    if not any_source:
        return 0

    # Optional demo references (may be missing in custom datasets)
    elizabeth = db.query(Person).filter(Person.primary_name == "Elizabeth II").first()
    abdulaziz = db.query(Person).filter(Person.primary_name == "Abdulaziz Ibn Saud").first()
    uk = db.query(Jurisdiction).filter(Jurisdiction.code == "GB").first()

    orders: list[Order] = []

    garter = Order(
        name="The Most Noble Order of the Garter (Demo)",
        jurisdiction_id=uk.id if uk else None,
        fons_honorum_person_id=elizabeth.id if elizabeth else None,
        founding_document_source_id=any_source.id,
        recognized_by=["GB"],
        granted_date=date(1348, 1, 1),
        grantor_person_id=elizabeth.id if elizabeth else None,
        notes="Seeded demo order for Day 7 validation.",
        valid_from=date(1348, 1, 1),
    )
    garter.sources = [any_source]
    orders.append(garter)

    self_styled = Order(
        name="Self-styled Sovereign Order of Example (Demo)",
        jurisdiction_id=None,
        fons_honorum_person_id=None,
        founding_document_source_id=None,
        recognized_by=[],
        granted_date=date(2000, 1, 1),
        grantor_person_id=abdulaziz.id if abdulaziz else None,
        notes="Seeded demo order intended to trigger fraud flags.",
        valid_from=date(2000, 1, 1),
    )
    self_styled.sources = [any_source]
    orders.append(self_styled)

    for o in orders:
        db.add(o)

    db.flush()

    if commit:
        db.commit()

    print(f"✅ Created {len(orders)} demo orders")
    return len(orders)


def create_demo_data(db: Session):
    print("\n🏛️  Royal BrAIn™ Demo Data Seeding")
    print("=" * 60)

    # Check if data already exists
    existing_persons = db.query(Person).count()
    if existing_persons > 0:
        print(f"\n⚠️  Warning: Database already contains {existing_persons} persons.")

        # In container/non-interactive runs, never block waiting for input.
        if not sys.stdin.isatty():
            print("ℹ️  Non-interactive mode detected. Keeping existing data.")
            seed_demo_orders_if_missing(db, commit=True)
            return

        response = input("Delete all existing data and reseed? (yes/no): ")
        if response.lower() != "yes":
            print("ℹ️  Keeping existing data. Seeding demo orders (if missing) only.")
            seed_demo_orders_if_missing(db, commit=True)
            return

        print("\n🗑️  Deleting existing data...")
        db.query(Relationship).delete()
        db.query(Order).delete()
        db.query(Person).delete()
        db.query(Family).delete()
        db.query(Source).delete()
        db.commit()
        print("✅ Existing data deleted.")

    print("\n📄 Creating source documents...")
    
    # Create sources
    sources = []
    source_data = [
        ("BIRTH_CERTIFICATE", "Windsor Register Office, Birth Certificate #W-1923-04-21", date(1923, 4, 21)),
        ("ROYAL_DECREE", "Royal Decree of Succession, Italian State Archives", date(1946, 6, 2)),
        ("HISTORICAL_RECORD", "Almanach de Gotha, 1950 Edition", date(1950, 1, 1)),
        ("LEGAL_DOCUMENT", "Spanish Royal Family Official Records", date(1975, 11, 22)),
        ("FAMILY_ARCHIVE", "House of Saud Official Genealogy", date(1932, 9, 23)),
        ("PUBLISHED_GENEALOGY", "Burke's Royal Families of the World, Vol. 1", date(1977, 1, 1)),
        ("HISTORICAL_RECORD", "Registro Civil de España, Marriage Certificate", date(1962, 5, 14)),
        ("BIRTH_CERTIFICATE", "Rome Municipal Registry, Birth Record", date(1934, 2, 2)),
        ("DEATH_CERTIFICATE", "Frogmore House, Death Certificate", date(1972, 5, 28)),
        ("ROYAL_DECREE", "Act of Succession to the Spanish Throne", date(2014, 6, 19)),
    ]

    for src_type, citation, issued in source_data:
        source = Source(
            source_type=src_type,
            citation=citation,
            issued_date=issued,
            valid_from=issued,
        )
        db.add(source)
        sources.append(source)

    db.flush()
    print(f"✅ Created {len(sources)} sources")

    print("\n👤 Creating persons...")

    # HOUSE 1: British Royal Family (Windsor)
    elizabeth_ii = Person(
        primary_name="Elizabeth II",
        sex="F",
        birth_date=date(1926, 4, 21),
        death_date=date(2022, 9, 8),
        valid_from=date(1926, 4, 21),
        notes="Queen of the United Kingdom 1952-2022",
    )
    elizabeth_ii.sources = [sources[0], sources[2]]

    philip = Person(
        primary_name="Prince Philip, Duke of Edinburgh",
        sex="M",
        birth_date=date(1921, 6, 10),
        death_date=date(2021, 4, 9),
        valid_from=date(1921, 6, 10),
        notes="Consort to Elizabeth II",
    )
    philip.sources = [sources[2]]

    charles_iii = Person(
        primary_name="Charles III",
        sex="M",
        birth_date=date(1948, 11, 14),
        valid_from=date(1948, 11, 14),
        notes="King of the United Kingdom 2022-present",
    )
    charles_iii.sources = [sources[0], sources[5]]

    william = Person(
        primary_name="Prince William of Wales",
        sex="M",
        birth_date=date(1982, 6, 21),
        valid_from=date(1982, 6, 21),
        notes="Heir apparent to British throne",
    )
    william.sources = [sources[0]]

    george = Person(
        primary_name="Prince George of Wales",
        sex="M",
        birth_date=date(2013, 7, 22),
        valid_from=date(2013, 7, 22),
        notes="Second in line to British throne",
    )
    george.sources = [sources[0]]

    # HOUSE 2: Spanish Royal Family (Bourbon)
    juan_carlos = Person(
        primary_name="Juan Carlos I",
        sex="M",
        birth_date=date(1938, 1, 5),
        valid_from=date(1938, 1, 5),
        notes="King of Spain 1975-2014",
    )
    juan_carlos.sources = [sources[3], sources[5]]

    felipe_vi = Person(
        primary_name="Felipe VI",
        sex="M",
        birth_date=date(1968, 1, 30),
        valid_from=date(1968, 1, 30),
        notes="King of Spain 2014-present",
    )
    felipe_vi.sources = [sources[3], sources[9]]

    leonor = Person(
        primary_name="Leonor, Princess of Asturias",
        sex="F",
        birth_date=date(2005, 10, 31),
        valid_from=date(2005, 10, 31),
        notes="Heir presumptive to Spanish throne",
    )
    leonor.sources = [sources[3]]

    sofia_spain = Person(
        primary_name="Infanta Sofía of Spain",
        sex="F",
        birth_date=date(2007, 4, 29),
        valid_from=date(2007, 4, 29),
        notes="Second daughter of Felipe VI",
    )
    sofia_spain.sources = [sources[3]]

    # HOUSE 3: Italian Royal Family (Savoy)
    vittorio_emanuele_iii = Person(
        primary_name="Vittorio Emanuele III",
        sex="M",
        birth_date=date(1869, 11, 11),
        death_date=date(1947, 12, 28),
        valid_from=date(1869, 11, 11),
        notes="Last King of Italy 1900-1946",
    )
    vittorio_emanuele_iii.sources = [sources[1], sources[2]]

    umberto_ii = Person(
        primary_name="Umberto II",
        sex="M",
        birth_date=date(1904, 9, 15),
        death_date=date(1983, 3, 18),
        valid_from=date(1904, 9, 15),
        notes="Last King of Italy May-June 1946",
    )
    umberto_ii.sources = [sources[1], sources[7]]

    vittorio_emanuele_prince = Person(
        primary_name="Vittorio Emanuele, Prince of Naples",
        sex="M",
        birth_date=date(1937, 2, 12),
        valid_from=date(1937, 2, 12),
        notes="Pretender to Italian throne",
    )
    vittorio_emanuele_prince.sources = [sources[1], sources[7]]

    emanuele_filiberto = Person(
        primary_name="Emanuele Filiberto, Prince of Venice",
        sex="M",
        birth_date=date(1972, 6, 22),
        valid_from=date(1972, 6, 22),
        notes="Heir to Savoy claim",
    )
    emanuele_filiberto.sources = [sources[1]]

    # HOUSE 4: Saudi Royal Family (Al Saud)
    abdulaziz = Person(
        primary_name="Abdulaziz Ibn Saud",
        sex="M",
        birth_date=date(1875, 1, 15),
        death_date=date(1953, 11, 9),
        valid_from=date(1875, 1, 15),
        notes="Founder of Saudi Arabia",
    )
    abdulaziz.sources = [sources[4]]

    salman = Person(
        primary_name="Salman bin Abdulaziz Al Saud",
        sex="M",
        birth_date=date(1935, 12, 31),
        valid_from=date(1935, 12, 31),
        notes="King of Saudi Arabia 2015-present",
    )
    salman.sources = [sources[4]]

    mohammed_bin_salman = Person(
        primary_name="Mohammed bin Salman Al Saud",
        sex="M",
        birth_date=date(1985, 8, 31),
        valid_from=date(1985, 8, 31),
        notes="Crown Prince of Saudi Arabia",
    )
    mohammed_bin_salman.sources = [sources[4]]

    persons = [
        elizabeth_ii, philip, charles_iii, william, george,
        juan_carlos, felipe_vi, leonor, sofia_spain,
        vittorio_emanuele_iii, umberto_ii, vittorio_emanuele_prince, emanuele_filiberto,
        abdulaziz, salman, mohammed_bin_salman,
    ]

    for person in persons:
        db.add(person)

    db.flush()
    print(f"✅ Created {len(persons)} persons")

    print("\n🔗 Creating relationships...")

    relationships = []

    # British Royal Family relationships
    # Marriage: Elizabeth II + Philip
    rel1 = Relationship(
        left_entity_type="person",
        left_entity_id=elizabeth_ii.id,
        right_entity_type="person",
        right_entity_id=philip.id,
        relationship_type="marriage",
        valid_from=date(1947, 11, 20),
    )
    rel1.sources = [sources[2]]

    # Parent-child: Elizabeth II -> Charles III
    rel2 = Relationship(
        left_entity_type="person",
        left_entity_id=elizabeth_ii.id,
        right_entity_type="person",
        right_entity_id=charles_iii.id,
        relationship_type="parent_child",
        valid_from=date(1948, 11, 14),
    )
    rel2.sources = [sources[0]]

    # Parent-child: Charles III -> William
    rel3 = Relationship(
        left_entity_type="person",
        left_entity_id=charles_iii.id,
        right_entity_type="person",
        right_entity_id=william.id,
        relationship_type="parent_child",
        valid_from=date(1982, 6, 21),
    )
    rel3.sources = [sources[0]]

    # Parent-child: William -> George
    rel4 = Relationship(
        left_entity_type="person",
        left_entity_id=william.id,
        right_entity_type="person",
        right_entity_id=george.id,
        relationship_type="parent_child",
        valid_from=date(2013, 7, 22),
    )
    rel4.sources = [sources[0]]

    # Spanish Royal Family relationships
    # Parent-child: Juan Carlos -> Felipe VI
    rel5 = Relationship(
        left_entity_type="person",
        left_entity_id=juan_carlos.id,
        right_entity_type="person",
        right_entity_id=felipe_vi.id,
        relationship_type="parent_child",
        valid_from=date(1968, 1, 30),
    )
    rel5.sources = [sources[3]]

    # Parent-child: Felipe VI -> Leonor
    rel6 = Relationship(
        left_entity_type="person",
        left_entity_id=felipe_vi.id,
        right_entity_type="person",
        right_entity_id=leonor.id,
        relationship_type="parent_child",
        valid_from=date(2005, 10, 31),
    )
    rel6.sources = [sources[3]]

    # Parent-child: Felipe VI -> Sofía
    rel7 = Relationship(
        left_entity_type="person",
        left_entity_id=felipe_vi.id,
        right_entity_type="person",
        right_entity_id=sofia_spain.id,
        relationship_type="parent_child",
        valid_from=date(2007, 4, 29),
    )
    rel7.sources = [sources[3]]

    # Italian Royal Family relationships
    # Parent-child: Vittorio Emanuele III -> Umberto II
    rel8 = Relationship(
        left_entity_type="person",
        left_entity_id=vittorio_emanuele_iii.id,
        right_entity_type="person",
        right_entity_id=umberto_ii.id,
        relationship_type="parent_child",
        valid_from=date(1904, 9, 15),
    )
    rel8.sources = [sources[1]]

    # Parent-child: Umberto II -> Vittorio Emanuele Prince
    rel9 = Relationship(
        left_entity_type="person",
        left_entity_id=umberto_ii.id,
        right_entity_type="person",
        right_entity_id=vittorio_emanuele_prince.id,
        relationship_type="parent_child",
        valid_from=date(1937, 2, 12),
    )
    rel9.sources = [sources[1]]

    # Parent-child: Vittorio Emanuele Prince -> Emanuele Filiberto
    rel10 = Relationship(
        left_entity_type="person",
        left_entity_id=vittorio_emanuele_prince.id,
        right_entity_type="person",
        right_entity_id=emanuele_filiberto.id,
        relationship_type="parent_child",
        valid_from=date(1972, 6, 22),
    )
    rel10.sources = [sources[1]]

    # Saudi Royal Family relationships
    # Parent-child: Abdulaziz -> Salman
    rel11 = Relationship(
        left_entity_type="person",
        left_entity_id=abdulaziz.id,
        right_entity_type="person",
        right_entity_id=salman.id,
        relationship_type="parent_child",
        valid_from=date(1935, 12, 31),
    )
    rel11.sources = [sources[4]]

    # Parent-child: Salman -> Mohammed bin Salman
    rel12 = Relationship(
        left_entity_type="person",
        left_entity_id=salman.id,
        right_entity_type="person",
        right_entity_id=mohammed_bin_salman.id,
        relationship_type="parent_child",
        valid_from=date(1985, 8, 31),
    )
    rel12.sources = [sources[4]]

    relationships = [rel1, rel2, rel3, rel4, rel5, rel6, rel7, rel8, rel9, rel10, rel11, rel12]

    for rel in relationships:
        db.add(rel)

    db.flush()
    print(f"✅ Created {len(relationships)} relationships")

    print("\n👨‍👩‍👧‍👦 Creating families...")

    # Check if jurisdictions exist (seeded from Day 6 migration)
    uk_jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.code == "GB").first()
    spain_jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.code == "ES").first()
    italy_jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.code == "IT").first()
    saudi_jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.code == "SA").first()

    print("\n🏅 Creating orders...")
    seed_demo_orders_if_missing(db, commit=False)

    families = []

    # House of Windsor
    windsor = Family(
        name="House of Windsor",
        notes="British Royal Family",
        valid_from=date(1917, 7, 17),
    )
    windsor.sources = [sources[0], sources[2]]

    # House of Bourbon (Spain)
    bourbon_spain = Family(
        name="House of Bourbon (Spain)",
        notes="Spanish Royal Family",
        valid_from=date(1700, 1, 1),
    )
    bourbon_spain.sources = [sources[3]]

    # House of Savoy
    savoy = Family(
        name="House of Savoy",
        notes="Italian Royal Family",
        valid_from=date(1003, 1, 1),
    )
    savoy.sources = [sources[1]]

    # House of Saud
    saud = Family(
        name="House of Saud",
        notes="Saudi Arabian Royal Family",
        valid_from=date(1744, 1, 1),
    )
    saud.sources = [sources[4]]

    families = [windsor, bourbon_spain, savoy, saud]

    for family in families:
        db.add(family)

    db.flush()
    print(f"✅ Created {len(families)} families")

    db.commit()

    print("\n" + "=" * 60)
    print("✅ DEMO DATA SEEDING COMPLETE")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   • {len(sources)} sources created")
    print(f"   • {len(persons)} persons created")
    orders_count = db.query(Order).count()
    print(f"   • {len(relationships)} relationships created")
    print(f"   • {orders_count} orders created")
    print(f"   • {len(families)} families created")
    print(f"\n🏛️  Royal Houses:")
    print(f"   1. House of Windsor (British)")
    print(f"      - 5 persons: Elizabeth II → Charles III → William → George")
    print(f"   2. House of Bourbon (Spanish)")
    print(f"      - 4 persons: Juan Carlos → Felipe VI → Leonor + Sofía")
    print(f"   3. House of Savoy (Italian)")
    print(f"      - 4 persons: Vittorio Emanuele III → Umberto II → VE Prince → EF")
    print(f"   4. House of Saud (Saudi)")
    print(f"      - 3 persons: Abdulaziz → Salman → Mohammed bin Salman")
    print(f"\n🎯 You can now:")
    print(f"   • View persons at /dashboard/data/persons")
    print(f"   • Build genealogy trees at /dashboard/genealogy")
    print(f"   • Test succession rules at /dashboard/succession")
    print(f"   • Validate orders at /dashboard/orders")
    print(f"   • Validate heraldry at /dashboard/heraldry")
    print("\n✨ System is ready for use!\n")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        create_demo_data(db)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
