def test_news_editorial_workflow(client):
    category = client.post("/gallery/categories", json={"name": "Culture"}).json()
    tag_response = client.post("/news/tags", json={"name": "Visual arts"})
    assert tag_response.status_code == 201

    created = client.post(
        "/news",
        json={
            "title": "A cultural event",
            "slug": "a-cultural-event",
            "category_id": category["id"],
            "tag_ids": [tag_response.json()["id"]],
            "sections": [
                {
                    "title": "Introduction",
                    "content": "Article content",
                    "element_order": ["title", "content"],
                }
            ],
        },
    )
    assert created.status_code == 201
    news = created.json()
    assert news["status"] == "draft"
    assert client.get("/news").json()["total"] == 0

    submitted = client.post(f"/news/{news['id']}/submit")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "in_review"

    reviewed = client.post(
        f"/news/{news['id']}/review",
        json={"status": "approved", "notes": "Ready to publish"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["revisions"][0]["action"] == "approved"

    published = client.post(f"/news/{news['id']}/publish", json={})
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    public = client.get("/news/slug/a-cultural-event")
    assert public.status_code == 200
    assert public.json()["tags"][0]["name"] == "Visual arts"
    assert client.get("/news").json()["total"] == 1
