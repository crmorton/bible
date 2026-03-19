from bible_api.api import format_osis_ref
import json

def test():
    test_cases = [
        ('Matt.5.17-Matt.5.18', 'Matthew 5:17-18'),
        ('Matt.26.24', 'Matthew 26:24'),
        ('John.5.46', 'John 5:46'),
        ('Luke.4.16-Luke.4.21', 'Luke 4:16-21'),
        ('Gen.1.1-Exod.1.1', 'Genesis 1:1 - Exodus 1:1'),
        ('Ps.119.1', 'Psalms 119:1'),
        ('1Cor.13.4-1Cor.13.8', '1 Corinthians 13:4-8')
    ]
    
    for osis, expected in test_cases:
        actual = format_osis_ref(osis)
        print(f"OSIS: {osis}")
        print(f"  Actual:   {actual}")
        print(f"  Expected: {expected}")
        print(f"  Match:    {actual == expected}")
        print()

if __name__ == "__main__":
    test()
