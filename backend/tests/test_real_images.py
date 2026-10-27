from backend.services.image_validator import measure_text_contrast


def test_low_contrast_ad_fails_wcag_aa():
    result = measure_text_contrast("test_data/images/low_contrast_ad.png")
    assert result["status"] == "fail"
    assert result["ratio"] < 2.0