from database.db_manager import db
import bcrypt

def seed_database():
    """Seed database with initial test data"""
    
    # Check if we already have vessels
    existing = db.fetch_one("SELECT COUNT(*) as count FROM vessels")
    if existing and existing['count'] > 0:
        print("Database already has data, skipping seed")
        return
    
    print("Seeding database with test data...")
    
    # Add test vessels
    test_vessels = [
        ('SP Dudinka', '9891234', 2015, 'Russia', 'dry-cargo', 35000),
        ('SP Norilsk', '9895678', 2018, 'Russia', 'dry-cargo', 42000),
        ('SP Murmansk', '9899012', 2020, 'Russia', 'tanker', 50000),
    ]
    
    for vessel in test_vessels:
        db.insert('vessels', {
            'name': vessel[0],
            'imo_number': vessel[1],
            'year_built': vessel[2],
            'flag': vessel[3],
            'vessel_type': vessel[4],
            'deadweight_mt': vessel[5],
            'is_active': 1
        })
    
    # Add test daily reports
    import datetime
    from dateutil.relativedelta import relativedelta
    
    vessels = db.fetch_all("SELECT id FROM vessels WHERE is_active = 1")
    
    for vessel in vessels:
        for days_ago in range(1, 10):
            report_date = datetime.datetime.now() - relativedelta(days=days_ago)
            db.insert('daily_reports', {
                'vessel_id': vessel['id'],
                'report_datetime': report_date.strftime('%Y-%m-%d 08:00:00'),
                'distance_run_nm': 250 + (days_ago % 50),
                'avg_speed_knots': 12.5,
                'rob_ifo_mt': 500 - (days_ago * 20),
                'rob_mgo_mt': 50 - (days_ago * 2),
                'consumption_ifo_24h_mt': 18.5,
                'consumption_mgo_24h_mt': 0.8,
                'operational_mode': 'laden',
                'next_port_name': 'Arkhangelsk',
                'is_approved': days_ago > 3
            })
    
    print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()