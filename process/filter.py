# Deduplication is done at the Storage Layer
# But it only filters the exact same posts via hash
# The problem is that most tgc just rephrase the same stuff (or just repost)
# Therefore we need to filter them in order to not get bankrupt from the token usage and to save water from the data canters xd

# So this module:
# Does a request to DB -> Shingle's Algorithm aka (MinHash / Jaccard Similarity) (links below) -> send formatted text to AI -> (maybe store a raw deduplicated version too)
# https://nlp.stanford.edu/IR-book/html/htmledition/near-duplicates-and-shingling-1.html 
# https://en.wikipedia.org/wiki/W-shingling
# https://blog.nelhage.com/post/fuzzy-dedup/