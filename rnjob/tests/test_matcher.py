from rnjob.matcher import score_job,rank_jobs
P={"experience_years":7,"minimum_lpa":18,"locations":["Delhi NCR"],"preferences":{"remote_ok":True},"strict_location":False,"notice_period_days":30,"apply_score_threshold":70}
def test_rn_matcher_and_items_bug_fixed():
    j={"role":"Senior React Native Engineer","location":"Gurugram","description":"7+ years React Native, TypeScript, Redux, Jest, Android/iOS. Salary 18-24 LPA. Notice period 30 days."}
    m=score_job(j,P);assert m["decision"]=="APPLY";assert m["score"]>70

def test_non_rn_is_hard_rejected():
    j={"role":"Senior React Engineer","location":"Delhi","description":"7+ years React, TypeScript. Salary 20 LPA."}
    m=score_job(j,P);assert "Not clearly a React Native role" in m["hard_failures"]
    assert rank_jobs([j],P)==[]

def test_salary_and_notice():
    j={"role":"React Native Engineer","location":"Remote","description":"5+ years React Native. 12-16 LPA. 15 days notice."}
    m=score_job(j,P);assert m["salary_range"]==[12.0,16.0];assert not m["notice_ok"]