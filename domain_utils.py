import re

def is_pronounceable(domain, tld):
    name = domain.replace(tld, "")

    if re.search(r"[bcdfghjklmnpqrstvwxyz]{3}", name):
        return False
    if re.search(r"[aeiou]{3}", name):
        return False
    if not re.search(r"[aeiou]", name):
        return False
    if not re.match(r"[bcdfghjklmnpqrstvwxyz][aeiou]", name):
        return False

    return True
