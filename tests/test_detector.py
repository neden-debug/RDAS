from edge.detector import CandidateDetector

def test_pothole_only_does_not_trigger():
    detector = CandidateDetector()
    assert not any(detector.update(0.12, 0.95, 0.2) for _ in range(10))

def test_sustained_multisignal_candidate_triggers_once():
    detector = CandidateDetector()
    results = [detector.update(0.95, 0.85, 0.9) for _ in range(15)]
    assert sum(results) == 1

def test_reject_out_of_range():
    detector = CandidateDetector()
    try:
        detector.update(1.5, 0, 0)
        assert False
    except ValueError:
        pass
