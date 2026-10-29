import rnjob.database as db

def test_schema_and_application(tmp_path,monkeypatch):
    monkeypatch.setattr(db,"DB_PATH",str(tmp_path/"x.db"));db.init_db();j=db.upsert_job({"company":"A","role":"RN","location":"Delhi","url":"https://example.com/1","description":"React Native"});db.create_application(j["id"],"SAVED");db.update_status(j["id"],"APPLIED","submitted manually");assert db.applications()[0]["status"]=="APPLIED";assert len(db.events(j["id"]))>=2