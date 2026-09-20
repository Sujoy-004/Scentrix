# Scentrix Real-Data Cold-Start Evaluation
Dataset: Atrafshan / Kalashi-Saed SentimentDrivenCommunityDetection (public GitHub) (users with scent votes=2454, perfumes=1090)
Source: https://github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection; license MIT.
Oracle: REAL held-out user scent votes >= 7 (dataset authors' positivity cut-off).
NOTE: content-itemknn here uses only brand/group/nature/origin/decade (no notes), so it
cannot share features with the oracle the way the intrinsic content baseline did.

k=1 (trials=300): popularity [P@5=0.0333, P@10=0.0300, R@10=0.0986, NDCG@10=0.0634] | top-rated [P@5=0.0007, P@10=0.0003, R@10=0.0002, NDCG@10=0.0003] | random [P@5=0.0033, P@10=0.0037, R@10=0.0068, NDCG@10=0.0059] | content-itemknn [P@5=0.0167, P@10=0.0113, R@10=0.0278, NDCG@10=0.0213]
k=2 (trials=300): popularity [P@5=0.0447, P@10=0.0360, R@10=0.0786, NDCG@10=0.0671] | top-rated [P@5=0.0013, P@10=0.0007, R@10=0.0044, NDCG@10=0.0028] | random [P@5=0.0047, P@10=0.0060, R@10=0.0097, NDCG@10=0.0084] | content-itemknn [P@5=0.0220, P@10=0.0167, R@10=0.0351, NDCG@10=0.0273]
k=3 (trials=300): popularity [P@5=0.0407, P@10=0.0327, R@10=0.0549, NDCG@10=0.0514] | top-rated [P@5=0.0020, P@10=0.0013, R@10=0.0047, NDCG@10=0.0025] | random [P@5=0.0040, P@10=0.0043, R@10=0.0101, NDCG@10=0.0065] | content-itemknn [P@5=0.0173, P@10=0.0163, R@10=0.0338, NDCG@10=0.0283]
k=5 (trials=184): popularity [P@5=0.0500, P@10=0.0424, R@10=0.0946, NDCG@10=0.0720] | top-rated [P@5=0.0000, P@10=0.0005, R@10=0.0014, NDCG@10=0.0007] | random [P@5=0.0076, P@10=0.0076, R@10=0.0171, NDCG@10=0.0118] | content-itemknn [P@5=0.0239, P@10=0.0234, R@10=0.0391, NDCG@10=0.0341]
Win-rate content-itemknn vs popularity (R@10): k=1=0.0567 k=2=0.0900 k=3=0.0833 k=5=0.1141
Caveats: single-market (Persian retailer) implicit vote behaviour; sparse (2,454 users with votes); trials without replacement = min(requested, eligible users).
