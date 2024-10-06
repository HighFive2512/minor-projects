import win32com.client

def resolve_dl(dist_list):
    outlook = win32com.client.Dispatch("Outlook.Application")
    dl = outlook.Session.CreateRecipient(dist_list)
    dl.Resolve()
    return dl

def check_for_dl(dist_list):
    dl = resolve_dl(dist_list)
    try:
        temp_list: list[str] = dl
        if dl.AddressEntry.GetExchangeDistributionList() != None:
            members = dl.AddressEntry.GetExchangeDistributionList().GetExchangeDistrtibutionListMembers()
            temp_members = []
            for eachmem in members:
                check_for_dl(eachmem)
                temp_members.append(eachmem)
        else:
            pass

    except Exception:
        return dl

