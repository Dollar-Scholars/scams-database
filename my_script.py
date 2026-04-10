import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scam_project.settings')
django.setup()


from scams.models import Scam

def main():
    print("ok")

if __name__ == "__main__":

    #create a new scam:
    Scam.objects.create(
    title="Scam phone call",
    description="Trying to get credit card info",
    scam_type="phishing",
    date_seen="2026-04-01",
    url_or_contact="076 579 46 34"
    )
    #create multiple scams
    Scam.objects.bulk_create([
    Scam(title="scam A", description="some really bad scam...", scam_type="phishing", date_seen="2026-04-01"),
    Scam(title="scam B", description="dangerous scan...", scam_type="sms", date_seen="2026-04-02"),
    ])

    #read existing data
    scams = Scam.objects.all().values()
    df = pd.DataFrame(scams)
    print(df)
    
    #filter
    Scam.objects.filter(scam_type="phishing")
    Scam.objects.filter(date_seen__year=2026)
    
    #delete a scam
    Scam.objects.get(title="scam B").delete()
    Scam.objects.get(title="scam A").delete()
    
    #read existing data
    scams = Scam.objects.all().values()
    df = pd.DataFrame(scams)
    print(df)
    main()