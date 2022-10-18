from flask import current_app
from models.user import User
from models.blog import Tag,Catalog, Article
from models.constants import Constant

from app import esClient

setmap = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    },
    "mappings": {
        "properties": {
            "id": {
                "type": "integer"
            },
            "title": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "excerpt": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "keyword": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "markdown": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "catalog_info": {
                "properties": {
                    "name": {
                        "search_analyzer": "ik_smart",
                        "analyzer": "ik_smart",
                        "type": "text"
                    },
                    "id": {
                        "type": "integer"
                    }
                }
            },
            "status": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "views": {
                "type": "integer"
            },
            "comments": {
                "type": "integer"
            },
            "likes": {
                "type": "integer"
            },
            "tags_info": {
                "properties": {
                    "name": {
                        "search_analyzer": "ik_smart",
                        "analyzer": "ik_smart",
                        "type": "text"
                    },
                    "id": {
                        "type": "integer"
                    }
                }
            }
        }
    }
}

def ESCreateIndex():
    try:
        if esClient.indices.exists(index=current_app.config["ELASTICSEARCH_INDEX"]) is True:
            esClient.indices.delete(index=current_app.config["ELASTICSEARCH_INDEX"])

        ret = esClient.indices.create(
            index = current_app.config["ELASTICSEARCH_INDEX"],
            body = setmap)
    except Exception as ex:
        print("ex,", ex)
        return
    
    page      = 1;
    page_size = 10;
    
    total= Article.query.count()
    while total > 0: 
        articles = Article.query.offset((page - 1) * page_size).limit(page_size).all()
        page+=1
        total -= len(articles)
    
        for article in articles:
            tags_info = [{"id": tag.id, "name": tag.name} for tag in article.tags.all()],
            catalog_info = {
                "id":           article.catalog.id,
                "name":         article.catalog.name,
            }
            body = {
                "id":           article.id,
                "title":        article.title,
                "excerpt":      article.excerpt,
                "keyword":      article.keyword,
                "markdown":     article.markdown,
                "status":       article.status,
                "tags_info":    tags_info,
                "catalog_info": catalog_info,
                "views":        article.views,
                "comments":     article.comments,
                "likes":        article.likes
            }

            try:
                ret = esClient.index(
                    index = current_app.config["ELASTICSEARCH_INDEX"], 
                    id = article.id,
                    body = body)
            except Exception as ex:
                print('ex=',ex)


def ESUpdateIndex(article):
    if current_app.config["ELASTICSEARCH_ON"]==False:
        return
    
    tags_info = [{"id": tag.id, "name": tag.name} for tag in article.tags.all()],
    catalog_info = {
        "id":   article.catalog.id,
        "name": article.catalog.name,
    }
    body = {
        "id":           article.id,
        "title":        article.title,
        "excerpt":      article.excerpt,
        "keyword":      article.keyword,
        "markdown":     article.markdown,
        "status":       article.status,
        "tags_info":    tags_info,
        "catalog_info": catalog_info,
        "views":        article.views,
        "comments":     article.comments,
        "likes":        article.likes
    }

    try:
        ret = esClient.index(
            index   = current_app.config["ELASTICSEARCH_INDEX"], 
            refresh = True,
            id      = article.id,
            body    = body )
    except Exception as ex:
        print('ex=',ex)


def ESSearchIndex(page, page_size, search_text):
    if current_app.config["ELASTICSEARCH_ON"]==False:
        return { "count": 0, "results": [] }
    
    try:
        ret = esClient.search(
            index = current_app.config["ELASTICSEARCH_INDEX"],
            body  = {
                "query": { 
                    "bool": { 
                              "should": [
                                   { "match": { "title":              search_text }}, 
                                   { "match": { "excerpt":            search_text }},
                                   { "match": { "keyword":            search_text }}, 
                                   { "match": { "markdown":           search_text }},
                                   { "match": { "tags_info.name":     search_text }},
                                   { "match": { "catalog_info.name":  search_text }}
                               ],
                               "must" : {
                                    "match" : {
                                        "status": Constant.ARTICLE_STATUS_PUBLISHED
                                    }
                               }
                            }
                }
            },
            from_ = (page - 1) * page_size,
            size = page_size
        )
    except Exception as ex:
        print("ex,",ex)
        return { "count": 0, "results": [] }
        
    articleList = {}
    if ret != None:
        if ret["hits"]:
            articleList = [{ "object": article["_source"] } for article in ret["hits"]["hits"]]
            return { "count": ret["hits"]["total"]["value"], "results": articleList }
  
    return { "count": 0, "results": [] }
