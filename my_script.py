import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scam_project.settings')
django.setup()


from scams.models import Scam

def main():
    print("")

if __name__ == "__main__":
    
    #delete all the data
    Scam.objects.all().delete()
    #create a new scam:
    Scam.objects.create(
    title = "scam title test 1",
    date_occurred = "2026-04-01",
    amount_lost = 23413,
    currency = "Other",
    platform = "platform1",
    description = "Some infos about the scam",
    phishing = True,
    url_or_contact = "scamers_email@test.com",

    scammer_name = "test_1",
    scammer_contact = "095 654 32 56",

    reporter_name = "may1",
    reporter_email = "my_email@test.com",
    reporter_phone = "123 456 78 90",
    country = "Switzerland"
    )
    
    #create multiple scams
    Scam.objects.bulk_create([
    Scam(title = "scam A", date_occurred = "2026-04-01", amount_lost = 23413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam B", date_occurred = "2026-04-01", amount_lost = 23413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    ])

    #read existing data
    scams = Scam.objects.all().values()
    df = pd.DataFrame(scams)
    print(df)
    
    #filter
    Scam.objects.filter(scam_type="financial")
    Scam.objects.filter(date_occurred__year=2026)
    
    #delete a scam
    Scam.objects.get(title="scam B").delete()
    Scam.objects.get(title="scam A").delete()
    
    #read existing data
    scams = Scam.objects.all().values()
    df = pd.DataFrame(scams)
    print(df)
    main()