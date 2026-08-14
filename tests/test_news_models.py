from app.models.categories import Category
from app.models.news import News, NewsRevision, NewsSection, NewsTag, Tag
from app.models.users import User


def test_news_models_persist_relationships_and_defaults(db):
    table_names = set(inspect(db.bind).get_table_names())
    assert {
        "news",
        "news_sections",
        "news_tags",
        "news_revisions",
        "tags",
    } <= table_names

    author = User(email="author@example.com", name="Author")
    editor = User(email="editor-news@example.com", name="Editor")
    category = Category(name="Culture")
    tag = Tag(name="Visual arts")
    db.add_all([author, editor, category, tag])
    db.flush()

    news = News(
        title="A cultural event",
        slug="a-cultural-event",
        category=category,
        author=author,
        editor=editor,
        sections=[
            NewsSection(content="Second section", position=2),
            NewsSection(
                title="Introduction",
                content="First section",
                element_order=["title", "content"],
                position=1,
            ),
        ],
        tag_links=[NewsTag(tag=tag)],
        revisions=[NewsRevision(editor=editor, action="submitted")],
    )
    db.add(news)
    db.commit()
    db.expire_all()

    stored = db.get(News, news.id)
    assert stored is not None
    assert stored.status == "draft"
    assert stored.featured is False
    assert stored.category is not None and stored.category.id == category.id
    assert stored.author is not None and stored.author.id == author.id
    assert stored.editor is not None and stored.editor.id == editor.id
    assert [section.position for section in stored.sections] == [1, 2]
    assert stored.sections[0].element_order == ["title", "content"]
    assert stored.tag_links[0].tag.name == "Visual arts"
    assert stored.revisions[0].editor_id == editor.id
    assert stored in category.news
    assert stored in author.authored_news
    assert stored in editor.edited_news
from sqlalchemy import inspect
