from finzanjir_ai.research.youtube import filter_youtube_video_results


def test_youtube_filter_keeps_only_https_video_urls():
    result = filter_youtube_video_results({
        "query": "space",
        "results": [
            {"title": "Video", "url": "https://www.youtube.com/watch?v=abc", "content": "about space"},
            {"title": "Short", "url": "https://youtu.be/xyz", "content": "short"},
            {"title": "Channel", "url": "https://www.youtube.com/@channel"},
            {"title": "Spoof", "url": "https://youtube.com.evil.example/watch?v=x"},
            {"title": "HTTP", "url": "http://youtube.com/watch?v=x"},
        ],
    })
    assert [item["title"] for item in result["results"]] == ["Video", "Short"]
    assert result["source"] == "youtube_public_web_index"
    assert "transkript o‘qilgani anglatmaydi" in result["note"]


def test_youtube_filter_handles_missing_or_invalid_results():
    assert filter_youtube_video_results({"results": None})["results"] == []
    assert filter_youtube_video_results({"results": [{"url": "javascript:alert(1)"}]})["results"] == []


def test_youtube_filter_deduplicates_tracking_variants_by_video_id():
    result = filter_youtube_video_results({
        "query": "hybrid retrieval",
        "results": [
            {
                "title": "Same video, lower score",
                "url": "https://www.youtube.com/watch?v=abc_123&xstg=tracking-one",
                "content": "Lower-ranked duplicate",
                "score": 0.5,
            },
            {
                "title": "Different video",
                "url": "https://youtu.be/xyz_789?si=tracking",
                "content": "Unique video",
                "score": 0.8,
            },
            {
                "title": "Same video, higher score",
                "url": "https://www.youtube.com/watch?xstg=tracking-two&v=abc_123",
                "content": "Best-ranked duplicate",
                "score": 0.95,
            },
        ],
    })

    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "Same video, higher score"
    assert result["results"][0]["url"] == "https://www.youtube.com/watch?v=abc_123"
    assert result["results"][1]["url"] == "https://www.youtube.com/watch?v=xyz_789"
