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
    #Scam.objects.all().delete()

    #create a new scam:
    Scam.objects.create(
    title = "test 1",
    date_occurred = "2026-01-11",
    amount_lost = 213,
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
    Scam(title = "scam A", date_occurred = "2025-10-17", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam B", date_occurred = "2025-12-18", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam C", date_occurred = "2025-11-23", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam D", date_occurred = "2025-11-07", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam E", date_occurred = "2025-12-08", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam F", date_occurred = "2025-11-13", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam G", date_occurred = "2025-10-27", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam H", date_occurred = "2026-02-18", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam I", date_occurred = "2026-01-13", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam J", date_occurred = "2026-01-17", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam K", date_occurred = "2026-02-18", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam L", date_occurred = "2026-01-23", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam M", date_occurred = "2026-01-17", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam N", date_occurred = "2026-03-28", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam O", date_occurred = "2026-03-13", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam P", date_occurred = "2025-10-17", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam Q", date_occurred = "2025-12-18", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam R", date_occurred = "2026-01-13", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam S", date_occurred = "2026-01-16", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam T", date_occurred = "2026-02-06", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam U", date_occurred = "2026-04-13", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam V", date_occurred = "2026-04-17", amount_lost = 213, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam W", date_occurred = "2026-03-18", amount_lost = 24413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam X", date_occurred = "2026-02-13", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam Y", date_occurred = "2026-02-23", amount_lost = 2413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    Scam(title = "scam Z", date_occurred = "2026-04-15", amount_lost = 25413, currency = "Other", platform = "platform1", description = "Some infos about the scam", phishing = True, url_or_contact = "scamers_email@test.com", scammer_name = "test_1", scammer_contact = "095 654 32 56", reporter_name = "may1", reporter_email = "my_email@test.com", reporter_phone = "123 456 78 90", country = "Switzerland"),
    ])

    #read existing data
    scams = Scam.objects.all().values()
    df = pd.DataFrame(scams)
    print(df)
    
    #filter
    Scam.objects.filter(scam_type="financial")
    Scam.objects.filter(date_seen__year=2026)
    
    #delete a scam
    #Scam.objects.get(title="scam B").delete()
    #Scam.objects.get(title="scam A").delete()
    
    #read existing data
    scams = Scam.objects.all().values()
    df = pd.DataFrame(scams)
    print(df)
    main()