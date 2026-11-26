def calculate_match(student_profile, job):
    student_skills = {skill.name for skill in student_profile.skills.all()}
    required_skills = {skill.name for skill in job.required_skills.all()}
    matched_skills = sorted(student_skills & required_skills)
    missing_skills = sorted(required_skills - student_skills)

    cgpa_ineligible = (
        job.min_cgpa is not None
        and (student_profile.cgpa is None or student_profile.cgpa < job.min_cgpa)
    )
    if cgpa_ineligible:
        match_score = 0.0
    elif not required_skills:
        match_score = 100.0
    else:
        match_score = round(len(matched_skills) / len(required_skills) * 100, 2)

    return {
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }
