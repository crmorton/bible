from bible_api.db import parse_ref

input_ref1 = 'Luke 4:16–21; 16:17; 18:31–33; 22:37; 24:25–27, 45–47;'
out1 = parse_ref(input_ref1)

input_ref2 = 'Matt. 5:17–18; 26:24; John 5:46'
out2 = parse_ref(input_ref2)
