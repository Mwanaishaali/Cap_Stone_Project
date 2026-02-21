import pandas as pd
import re

# ==========================
# 1 Job Title Patterns (Regex -> Standardized Title)
#
# ==========================
JOB_TITLE_PATTERNS = {

    # ── Technology ──────────────────────────────────────────────────────────
    r".*software.*engineer.*|.*engineer.*software.*|.*software.*dev.*":              "Software Engineer",
    r".*data.*scientist.*|.*scientist.*data.*":                                       "Data Scientist",
    r".*data.*analyst.*|.*analyst.*data.*":                                           "Data Analyst",
    r".*machine.*learning.*|\bml\b.*engineer.*|.*ai.*researcher.*":                  "Machine Learning Engineer",
    r".*ai.*engineer.*|.*artificial.*intelligence.*engineer.*":                       "Machine Learning Engineer",
    r".*web.*developer.*|.*web.*dev.*|.*web.*designer.*":                            "Web Developer",
    r".*applications.*developer.*|.*apps.*developer.*|.*programmer.*applications.*": "Web Developer",
    r".*systems.*developer.*|.*systems.*programmer.*|.*programmer.*systems.*":       "Software Engineer",
    r".*multimedia.*programmer.*|.*multimedia.*developer.*|.*multimedia.*specialist.*": "Web Developer",
    r".*computer.*games.*|.*games.*developer.*":                                     "Software Engineer",
    r".*backend.*developer.*|.*back.end.*dev.*":                                     "Backend Developer",
    r".*frontend.*developer.*|.*front.end.*dev.*":                                   "Frontend Developer",
    r".*it.*support.*|.*tech.*support.*|.*helpdesk.*|.*technical.*support.*":        "IT Support Specialist",
    r".*system.*admin.*|.*sysadmin.*|.*information.*systems.*manager.*":             "System Administrator",
    r".*devops.*|.*site.*reliability.*|\bsre\b":                                     "DevOps Engineer",
    r".*cloud.*engineer.*|.*cloud.*architect.*":                                     "Cloud Engineer",
    r".*cybersecurity.*|.*security.*analyst.*|.*information.*security.*":            "Cybersecurity Analyst",
    r".*product.*manager.*|.*product.*owner.*":                                      "Product Manager",
    r".*ux.*designer.*|.*ui.*designer.*|.*user.*experience.*":                       "UX/UI Designer",
    r".*network.*engineer.*|.*communications.*engineer.*|.*engineer.*communications.*": "Network Engineer",
    r".*database.*admin.*|\bdba\b|.*data.*processing.*manager.*":                    "Database Administrator",
    r".*it.*consultant.*|.*consultant.*it.*|.*technical.*author.*":                  "IT Consultant",

    # ── Engineering (non-IT) ────────────────────────────────────────────────
    r".*civil.*engineer.*|.*engineer.*civil.*|.*consulting.*civil.*|.*contracting.*civil.*": "Civil Engineer",
    r".*electrical.*engineer.*|.*engineer.*electrical.*":                            "Electrical Engineer",
    r".*mechanical.*engineer.*|.*engineer.*mechanical.*":                            "Mechanical Engineer",
    r".*industrial.*engineer.*|.*engineer.*industrial.*":                            "Industrial Engineer",
    r".*structural.*engineer.*|.*engineer.*structural.*":                            "Structural Engineer",
    r".*systems.*engineer.*|.*systems.*analyst.*":                                   "Systems Engineer",
    r".*chemical.*engineer.*|.*engineer.*chemical.*":                                "Chemical Engineer",
    r".*aerospace.*engineer.*|.*aeronautical.*engineer.*|.*engineer.*aeronautical.*": "Aerospace Engineer",
    r".*environmental.*engineer.*|.*engineer.*environmental.*":                      "Environmental Engineer",
    r".*biomedical.*engineer.*|.*engineer.*biomedical.*":                            "Biomedical Engineer",
    r".*manufacturing.*engineer.*|.*engineer.*manufacturing.*":                      "Manufacturing Engineer",
    r".*production.*engineer.*|.*engineer.*production.*":                            "Manufacturing Engineer",
    r".*materials.*engineer.*|.*engineer.*materials.*|.*metallurgist.*":             "Materials Engineer",
    r".*mining.*engineer.*|.*engineer.*mining.*":                                    "Mining Engineer",
    r".*petroleum.*engineer.*|.*engineer.*petroleum.*|.*drilling.*engineer.*":       "Petroleum Engineer",
    r".*energy.*engineer.*|.*engineer.*energy.*|.*energy.*manager.*":                "Energy Engineer",
    r".*water.*engineer.*|.*engineer.*water.*|.*hydrologist.*|.*hydrogeologist.*":   "Water Engineer",
    r".*building.*services.*engineer.*|.*engineer.*building.*":                      "Building Engineer",
    r".*control.*instrumentation.*|.*engineer.*control.*":                           "Control Engineer",
    r".*maintenance.*engineer.*|.*engineer.*maintenance.*":                          "Maintenance Engineer",
    r".*agricultural.*engineer.*|.*engineer.*agricultural.*":                        "Agricultural Engineer",
    r".*automotive.*engineer.*|.*engineer.*automotive.*":                            "Automotive Engineer",
    r".*electronics.*engineer.*|.*engineer.*electronics.*":                          "Electronics Engineer",
    r".*geologist.*|.*geophysicist.*|.*geoscientist.*|.*geochemist.*|.*mudlogger.*": "Geologist",
    r".*surveyor.*|.*quantity.*surveyor.*":                                          "Surveyor",
    r".*architect\b.*|.*landscape.*architect.*|.*architectural.*technologist.*":     "Architect",
    r".*town.*planner.*|.*transport.*planner.*":                                     "Planner",
    r".*naval.*architect.*":                                                         "Naval Architect",
    r".*cartographer.*|.*geographical.*information.*":                               "Geospatial Specialist",
    r".*meteorologist.*|.*oceanographer.*":                                          "Environmental Scientist",
    r".*site.*engineer.*|.*engineer.*site.*|.*engineer.*land.*":                    "Civil Engineer",
    r".*broadcast.*engineer.*|.*engineer.*broadcast.*":                              "Electronics Engineer",

    # ── Healthcare ──────────────────────────────────────────────────────────
    r".*nurse.*|.*nursing.*|.*midwife.*|.*midwifery.*":                             "Registered Nurse",
    r".*doctor.*|.*physician.*|.*medical.*officer.*|.*general.*practice.*":          "Medical Doctor",
    r".*pharmacist.*|.*pharmacy.*":                                                  "Pharmacist",
    r".*therapist.*|.*psychotherapist.*|.*dramatherapist.*|.*art.*therapist.*":     "Therapist",
    r".*psychologist.*|.*psychiatrist.*":                                            "Psychologist",
    r".*clinician.*|.*clinical.*officer.*|.*clinical.*scientist.*":                 "Healthcare Clinician",
    r".*dentist.*|.*dental.*":                                                       "Dentist",
    r".*surgeon.*":                                                                  "Surgeon",
    r".*radiographer.*|.*radiologist.*":                                             "Radiologist",
    r".*public.*health.*|.*epidemiologist.*|.*health.*promotion.*":                 "Public Health Specialist",
    r".*physiotherapist.*|.*occupational.*therapist.*|.*speech.*language.*":        "Allied Health Professional",
    r".*paramedic.*|.*ambulance.*":                                                  "Paramedic",
    r".*dietitian.*|.*nutritionist.*|.*nutritional.*":                              "Dietitian",
    r".*optician.*|.*optometrist.*|.*ophthalmologist.*|.*orthoptist.*":             "Optometrist",
    r".*chiropodist.*|.*podiatrist.*|.*chiropractor.*|.*osteopath.*":              "Allied Health Professional",
    r".*acupuncturist.*|.*homeopath.*|.*herbalist.*|.*phytotherapist.*":           "Allied Health Professional",
    r".*audiolog.*|.*haematologist.*|.*oncologist.*|.*pathologist.*":              "Medical Specialist",
    r".*health.*visitor.*|.*health.*inspector.*|.*health.*safety.*":               "Health And Safety Specialist",
    r".*medical.*laboratory.*|.*biomedical.*scientist.*|.*clinical.*biochemist.*": "Medical Lab Scientist",
    r".*embryologist.*|.*cytogeneticist.*|.*immunologist.*":                       "Medical Scientist",
    r".*veterinary.*|.*vet\b.*":                                                    "Veterinarian",
    r".*ambulance.*person.*":                                                       "Paramedic",

    # ── Business & Finance ──────────────────────────────────────────────────
    r".*accountant.*|.*accounting.*technician.*|.*chartered.*accountant.*":         "Accountant",
    r".*financial.*analyst.*|.*finance.*analyst.*|.*financial.*risk.*analyst.*":    "Financial Analyst",
    r".*business.*analyst.*":                                                        "Business Analyst",
    r".*marketing.*|.*market.*researcher.*|.*media.*buyer.*|.*media.*planner.*":    "Marketing Specialist",
    r".*sales.*rep.*|.*sales.*exec.*|.*sales.*agent.*|.*sales.*professional.*":     "Sales Representative",
    r".*operations.*manager.*|.*ops.*manager.*":                                    "Operations Manager",
    r".*project.*manager.*|.*programme.*manager.*":                                 "Project Manager",
    r".*\bhr\b.*|.*human.*resource.*|.*personnel.*officer.*|.*recruitment.*":       "HR Specialist",
    r".*supply.*chain.*|.*logistics.*|.*procurement.*|.*purchasing.*|.*buyer.*":    "Supply Chain Specialist",
    r".*auditor.*|.*internal.*audit.*":                                             "Auditor",
    r".*actuary.*|.*actuarial.*":                                                   "Actuary",
    r".*economist.*":                                                               "Economist",
    r".*management.*consultant.*|.*consultant\b.*":                                 "Consultant",
    r".*banker.*|.*banking.*|.*investment.*banker.*|.*retail.*banker.*":           "Banker",
    r".*financial.*adviser.*|.*financial.*planner.*|.*financial.*manager.*":       "Financial Adviser",
    r".*financial.*controller.*|.*financial.*trader.*|.*trader.*|.*dealer.*":      "Financial Trader",
    r".*insurance.*|.*loss.*adjuster.*|.*underwriter.*":                           "Insurance Professional",
    r".*tax.*inspector.*|.*tax.*adviser.*|.*tax.*professional.*":                  "Tax Professional",
    r".*risk.*manager.*|.*risk.*analyst.*":                                         "Risk Analyst",
    r".*company.*secretary.*|.*comptroller.*|.*corporate.*treasurer.*":            "Corporate Officer",
    r".*chief.*executive.*|\bceo\b|\bcfo\b|\bcto\b|\bcoo\b|\bcmo\b":              "Executive",
    r".*chief.*officer.*|.*chief.*of.*staff.*":                                    "Executive",
    r".*office.*manager.*|.*facilities.*manager.*":                                "Office Administrator",
    r".*customer.*service.*|.*call.*centre.*":                                     "Customer Service",
    r".*estate.*agent.*|.*estate.*manager.*":                                      "Estate Agent",
    r".*pensions.*consultant.*|.*pension.*scheme.*":                               "Financial Adviser",
    r".*purchasing.*manager.*":                                                     "Supply Chain Specialist",

    # ── Policy & Research ───────────────────────────────────────────────────
    r".*policy.*analyst.*|.*policy.*officer.*|.*policy.*advisor.*":                "Policy Analyst",
    r".*research.*analyst.*|.*research.*officer.*|.*researcher.*|.*research.*scientist.*": "Research Analyst",
    r".*statistician.*|.*operational.*researcher.*":                               "Research Analyst",
    r".*intelligence.*analyst.*|.*lobbyist.*|.*public.*affairs.*":                 "Policy Analyst",
    r".*government.*social.*research.*|.*social.*researcher.*":                    "Research Analyst",

    # ── Education ───────────────────────────────────────────────────────────
    r".*teacher.*|.*early.*years.*|.*primary.*school.*teacher.*|.*secondary.*school.*teacher.*": "Teacher",
    r".*lecturer.*|.*further.*education.*|.*higher.*education.*lecturer.*":        "Lecturer",
    r".*professor.*|.*associate.*professor.*":                                     "Professor",
    r".*tutor.*|.*music.*tutor.*|.*private.*music.*teacher.*":                    "Tutor",
    r".*curriculum.*|.*instructional.*designer.*":                                 "Curriculum Developer",
    r".*education.*administrator.*|.*education.*officer.*":                        "Education Administrator",
    r".*careers.*adviser.*|.*guidance.*worker.*|.*learning.*mentor.*":            "Education Administrator",
    r".*tefl.*|.*esol.*|.*english.*foreign.*language.*|.*english.*second.*language.*": "Teacher",
    r".*special.*educational.*needs.*":                                            "Teacher",
    r".*adult.*education.*|.*community.*education.*":                              "Teacher",

    # ── Law & Public Service ─────────────────────────────────────────────────
    r".*lawyer.*|.*barrister.*|.*solicitor.*|.*advocate.*|.*attorney.*":          "Lawyer",
    r".*legal.*executive.*|.*chartered.*legal.*|.*licensed.*conveyancer.*":       "Lawyer",
    r".*patent.*attorney.*|.*trade.*mark.*attorney.*|.*patent.*examiner.*":       "Lawyer",
    r".*police.*|.*detective.*":                                                   "Police Officer",
    r".*civil.*servant.*|.*civil.*service.*|.*government.*officer.*|.*local.*government.*": "Government Officer",
    r".*diplomatic.*|.*immigration.*officer.*":                                    "Government Officer",
    r".*prison.*officer.*|.*probation.*officer.*":                                "Government Officer",
    r".*social.*worker.*|.*community.*worker.*|.*youth.*worker.*":                "Social Worker",
    r".*charity.*|.*voluntary.*|.*aid.*worker.*|.*international.*aid.*":          "Charity Worker",
    r".*trading.*standards.*|.*equality.*diversity.*|.*race.*relations.*":        "Government Officer",
    r".*firefighter.*|.*fire.*service.*":                                         "Emergency Services",
    r".*armed.*forces.*|.*military.*":                                            "Armed Forces",

    # ── Science ──────────────────────────────────────────────────────────────
    r".*chemist.*|.*analytical.*chemist.*|.*biochemist.*":                        "Scientist",
    r".*biologist.*|.*microbiologist.*|.*ecologist.*":                            "Scientist",
    r".*physicist.*|.*astronomer.*|.*toxicologist.*":                             "Scientist",
    r".*forensic.*scientist.*":                                                    "Scientist",
    r".*food.*technologist.*|.*brewing.*technologist.*|.*colour.*technologist.*": "Scientist",
    r".*soil.*scientist.*|.*marine.*scientist.*|.*water.*quality.*scientist.*":   "Scientist",
    r".*product.*process.*development.*scientist.*|.*scientist.*life.*sciences.*": "Scientist",

    # ── Arts, Media & Communication ─────────────────────────────────────────
    r".*artist.*|.*fine.*artist.*|.*illustrator.*|.*animator.*":                  "Creative Artist",
    r".*graphic.*designer.*|.*designer.*graphic.*":                               "Creative Artist",
    r".*fashion.*designer.*|.*textile.*designer.*|.*designer.*fashion.*|.*designer.*textile.*": "Creative Artist",
    r".*interior.*designer.*|.*designer.*interior.*|.*exhibition.*designer.*":   "Creative Artist",
    r".*jewellery.*designer.*|.*ceramics.*designer.*|.*furniture.*designer.*":   "Creative Artist",
    r".*set.*designer.*|.*designer.*television.*|.*production.*designer.*":       "Creative Artist",
    r".*industrial.*product.*designer.*|.*designer.*industrial.*":               "Creative Artist",
    r".*journalist.*|.*reporter.*|.*correspondent.*|.*broadcast.*journalist.*":  "Journalist",
    r".*newspaper.*journalist.*|.*magazine.*journalist.*":                        "Journalist",
    r".*writer.*|.*author.*|.*copywriter.*|.*content.*creator.*|.*proofreader.*": "Writer",
    r".*science.*writer.*|.*copy\b.*":                                            "Writer",
    r".*photographer.*|.*press.*photographer.*":                                  "Photographer",
    r".*video.*editor.*|.*film.*editor.*|.*editor.*film.*":                      "Film/Video Producer",
    r".*television.*producer.*|.*film.*producer.*|.*radio.*producer.*":          "Film/Video Producer",
    r".*television.*production.*|.*production.*assistant.*":                      "Film/Video Producer",
    r".*camera.*operator.*|.*sound.*technician.*|.*lighting.*technician.*":      "Film/Video Producer",
    r".*broadcast.*presenter.*|.*presenter.*broadcasting.*":                      "Journalist",
    r".*public.*relations.*":                                                     "PR / Communications",
    r".*advertising.*account.*|.*advertising.*art.*|.*advertising.*copy.*":      "Marketing Specialist",
    r".*musician.*|.*dancer.*|.*actor.*|.*theatre.*director.*":                  "Performing Artist",
    r".*stage.*manager.*|.*theatre.*manager.*":                                   "Performing Artist",
    r".*curator.*|.*archivist.*|.*librarian.*|.*records.*manager.*":             "Library/Museum Professional",
    r".*museum.*|.*gallery.*|.*heritage.*manager.*|.*conservation.*officer.*":   "Library/Museum Professional",

    # ── Hospitality & Service ────────────────────────────────────────────────
    r".*chef.*|.*cook.*|.*culinary.*|.*catering.*manager.*":                     "Chef",
    r".*waiter.*|.*barista.*|.*bartender.*|.*server.*|.*cabin.*crew.*|.*air.*cabin.*": "Hospitality Staff",
    r".*hotel.*manager.*|.*front.*desk.*|.*concierge.*":                         "Hospitality Staff",
    r".*restaurant.*manager.*|.*fast.*food.*manager.*|.*public.*house.*manager.*": "Hospitality Staff",
    r".*leisure.*centre.*|.*fitness.*centre.*|.*theme.*park.*|.*tourism.*officer.*": "Hospitality Staff",
    r".*travel.*agency.*|.*holiday.*representative.*|.*tour.*manager.*":         "Hospitality Staff",
    r".*event.*organiser.*|.*conference.*centre.*manager.*":                     "Hospitality Staff",

    # ── Transport & Logistics ────────────────────────────────────────────────
    r".*pilot.*|.*aviator.*|.*flight.*officer.*|.*airline.*pilot.*":             "Pilot",
    r".*air.*traffic.*controller.*":                                             "Air Traffic Controller",
    r".*driver.*|.*chauffeur.*":                                                 "Driver",
    r".*merchant.*navy.*|.*ship.*broker.*|.*air.*broker.*|.*freight.*forwarder.*": "Logistics Professional",
    r".*logistics.*|.*distribution.*manager.*|.*transport.*manager.*|.*passenger.*transport.*": "Logistics Professional",
    r".*warehouse.*manager.*":                                                   "Logistics Professional",

    # ── Agriculture & Environment ────────────────────────────────────────────
    r".*farmer.*|.*farm.*manager.*|.*agronomist.*|.*agricultural.*consultant.*": "Farmer",
    r".*horticulturist.*|.*horticultural.*|.*arboriculturist.*|.*tree.*surgeon.*": "Horticulturist",
    r".*nature.*conservation.*|.*forest.*|.*ranger.*|.*warden.*":               "Environmental Specialist",
    r".*environmental.*consultant.*|.*environmental.*manager.*|.*waste.*management.*": "Environmental Specialist",
    r".*fish.*farm.*|.*fisheries.*":                                             "Environmental Specialist",

    # ── Sports & Fitness ─────────────────────────────────────────────────────
    r".*sports.*coach.*|.*sports.*development.*|.*sports.*administrator.*|.*administrator.*sports.*": "Sports Professional",
    r".*fitness.*centre.*manager.*|.*exercise.*physiologist.*":                  "Sports Professional",
    r".*outdoor.*activities.*|.*outdoor.*education.*":                           "Sports Professional",
}

# 2 Career Family Map
CAREER_FAMILY_MAP = {
    # Technology
    "Software Engineer":            "Technology",
    "Data Scientist":               "Technology",
    "Data Analyst":                 "Technology",
    "Machine Learning Engineer":    "Technology",
    "Web Developer":                "Technology",
    "Backend Developer":            "Technology",
    "Frontend Developer":           "Technology",
    "IT Support Specialist":        "Technology",
    "System Administrator":         "Technology",
    "DevOps Engineer":              "Technology",
    "Cloud Engineer":               "Technology",
    "Cybersecurity Analyst":        "Technology",
    "Product Manager":              "Technology",
    "UX/UI Designer":               "Technology",
    "Network Engineer":             "Technology",
    "Database Administrator":       "Technology",
    "IT Consultant":                "Technology",

    # Engineering
    "Civil Engineer":               "Engineering",
    "Mechanical Engineer":          "Engineering",
    "Electrical Engineer":          "Engineering",
    "Industrial Engineer":          "Engineering",
    "Structural Engineer":          "Engineering",
    "Systems Engineer":             "Engineering",
    "Chemical Engineer":            "Engineering",
    "Aerospace Engineer":           "Engineering",
    "Environmental Engineer":       "Engineering",
    "Biomedical Engineer":          "Engineering",
    "Manufacturing Engineer":       "Engineering",
    "Materials Engineer":           "Engineering",
    "Mining Engineer":              "Engineering",
    "Petroleum Engineer":           "Engineering",
    "Energy Engineer":              "Engineering",
    "Water Engineer":               "Engineering",
    "Building Engineer":            "Engineering",
    "Control Engineer":             "Engineering",
    "Maintenance Engineer":         "Engineering",
    "Agricultural Engineer":        "Engineering",
    "Automotive Engineer":          "Engineering",
    "Electronics Engineer":         "Engineering",
    "Naval Architect":              "Engineering",
    "Geologist":                    "Engineering",
    "Surveyor":                     "Engineering",
    "Architect":                    "Engineering",
    "Planner":                      "Engineering",
    "Geospatial Specialist":        "Engineering",
    "Environmental Scientist":      "Engineering",

    # Healthcare
    "Registered Nurse":             "Healthcare",
    "Medical Doctor":               "Healthcare",
    "Pharmacist":                   "Healthcare",
    "Therapist":                    "Healthcare",
    "Psychologist":                 "Healthcare",
    "Healthcare Clinician":         "Healthcare",
    "Dentist":                      "Healthcare",
    "Surgeon":                      "Healthcare",
    "Radiologist":                  "Healthcare",
    "Public Health Specialist":     "Healthcare",
    "Allied Health Professional":   "Healthcare",
    "Paramedic":                    "Healthcare",
    "Dietitian":                    "Healthcare",
    "Optometrist":                  "Healthcare",
    "Medical Specialist":           "Healthcare",
    "Health And Safety Specialist": "Healthcare",
    "Medical Lab Scientist":        "Healthcare",
    "Medical Scientist":            "Healthcare",
    "Veterinarian":                 "Healthcare",

    # Business & Finance
    "Accountant":                   "Business And Finance",
    "Financial Analyst":            "Business And Finance",
    "Business Analyst":             "Business And Finance",
    "Marketing Specialist":         "Business And Finance",
    "Sales Representative":         "Business And Finance",
    "Operations Manager":           "Business And Finance",
    "Project Manager":              "Business And Finance",
    "HR Specialist":                "Business And Finance",
    "Supply Chain Specialist":      "Business And Finance",
    "Auditor":                      "Business And Finance",
    "Actuary":                      "Business And Finance",
    "Economist":                    "Business And Finance",
    "Consultant":                   "Business And Finance",
    "Banker":                       "Business And Finance",
    "Financial Adviser":            "Business And Finance",
    "Financial Trader":             "Business And Finance",
    "Insurance Professional":       "Business And Finance",
    "Tax Professional":             "Business And Finance",
    "Risk Analyst":                 "Business And Finance",
    "Corporate Officer":            "Business And Finance",
    "Executive":                    "Business And Finance",
    "Office Administrator":         "Business And Finance",
    "Customer Service":             "Business And Finance",
    "Estate Agent":                 "Business And Finance",

    # Policy & Research
    "Policy Analyst":               "Policy And Research",
    "Research Analyst":             "Policy And Research",

    # Science
    "Scientist":                    "Science",

    # Education
    "Teacher":                      "Education",
    "Lecturer":                     "Education",
    "Professor":                    "Education",
    "Tutor":                        "Education",
    "Curriculum Developer":         "Education",
    "Education Administrator":      "Education",

    # Law & Public Service
    "Lawyer":                       "Law And Public Service",
    "Police Officer":               "Law And Public Service",
    "Government Officer":           "Law And Public Service",
    "Social Worker":                "Law And Public Service",
    "Charity Worker":               "Law And Public Service",
    "Emergency Services":           "Law And Public Service",
    "Armed Forces":                 "Law And Public Service",

    # Arts & Media
    "Creative Artist":              "Arts And Media",
    "Journalist":                   "Arts And Media",
    "Writer":                       "Arts And Media",
    "Photographer":                 "Arts And Media",
    "Film/Video Producer":          "Arts And Media",
    "PR / Communications":          "Arts And Media",
    "Performing Artist":            "Arts And Media",
    "Library/Museum Professional":  "Arts And Media",

    # Hospitality & Service
    "Chef":                         "Hospitality And Service",
    "Hospitality Staff":            "Hospitality And Service",

    # Transport
    "Pilot":                        "Transport And Aviation",
    "Air Traffic Controller":       "Transport And Aviation",
    "Driver":                       "Transport And Aviation",
    "Logistics Professional":       "Transport And Aviation",

    # Agriculture & Environment
    "Farmer":                       "Agriculture",
    "Horticulturist":               "Agriculture",
    "Environmental Specialist":     "Agriculture",

    # Sports
    "Sports Professional":          "Sports And Fitness",
}


# 3 Fallback function for uncategorized jobs
def assign_fallback_family(title):
    title = str(title).lower()
    if any(k in title for k in ['policy', 'ministry', 'public sector', 'lobbyist']):
        return 'Policy And Research'
    elif any(k in title for k in ['research', 'researcher', 'statistician']):
        return 'Policy And Research'
    elif any(k in title for k in ['developer', 'programmer', 'software', 'devops',
                                   'cyber', 'network', 'database', 'machine learning',
                                   'artificial intelligence', 'ux', 'ui', 'cloud']):
        return 'Technology'
    elif any(k in title for k in ['marketing', 'sales', 'business', 'operations', 'consultant',
                                   'project', 'supply', 'procurement', 'hr', 'human resource',
                                   'recruiter', 'auditor', 'economist', 'strategy', 'finance',
                                   'insurance', 'banker', 'trader', 'tax', 'accountant']):
        return 'Business And Finance'
    elif any(k in title for k in ['teacher', 'lecturer', 'professor', 'tutor',
                                   'instructor', 'education', 'curriculum', 'tefl']):
        return 'Education'
    elif any(k in title for k in ['nurse', 'doctor', 'physician', 'pharmacist', 'clinical',
                                   'health', 'dental', 'medical', 'therapist', 'surgeon',
                                   'paramedic', 'dietitian', 'optician', 'psychologist',
                                   'psychiatrist', 'veterinary']):
        return 'Healthcare'
    elif any(k in title for k in ['engineer', 'technician', 'technologist', 'surveyor',
                                   'architect', 'geologist', 'metallurgist', 'planner']):
        return 'Engineering'
    elif any(k in title for k in ['scientist', 'chemist', 'biologist', 'physicist',
                                   'microbiologist', 'ecologist', 'toxicologist']):
        return 'Science'
    elif any(k in title for k in ['artist', 'designer', 'writer', 'journalist', 'photographer',
                                   'media', 'content', 'creative', 'curator', 'librarian',
                                   'museum', 'gallery', 'broadcaster', 'editor', 'animator']):
        return 'Arts And Media'
    elif any(k in title for k in ['chef', 'hospitality', 'barista', 'waiter', 'hotel',
                                   'cook', 'restaurant', 'catering', 'tourism', 'travel']):
        return 'Hospitality And Service'
    elif any(k in title for k in ['lawyer', 'advocate', 'attorney', 'barrister', 'solicitor',
                                   'police', 'social worker', 'civil servant', 'government',
                                   'charity', 'prison', 'probation', 'firefighter', 'military']):
        return 'Law And Public Service'
    elif any(k in title for k in ['pilot', 'driver', 'aviator', 'transport', 'logistics',
                                   'freight', 'warehouse', 'air traffic']):
        return 'Transport And Aviation'
    elif any(k in title for k in ['farmer', 'agronomist', 'agriculture', 'horticulturist',
                                   'arboriculturist', 'forester', 'conservation', 'ecology',
                                   'environmental', 'ranger', 'warden']):
        return 'Agriculture'
    elif any(k in title for k in ['sports', 'fitness', 'coach', 'athletic', 'exercise']):
        return 'Sports And Fitness'
    # FIX Issue 3: short career label patterns that appear in career_dataset
    # but were not matched by the longer patterns above.
    elif any(k in title for k in ['clerk', 'administrator', 'assistant', 'officer',
                                   'coordinator', 'specialist', 'representative',
                                   'manager', 'supervisor', 'director']):
        return 'Business And Finance'
    elif any(k in title for k in ['analyst']):
        return 'Business And Finance'
    else:
        return 'Other'


# 4 Standardize job titles
def standardize_job_title(df, verbose=True):
    df = df.copy()

    JOB_TITLE_ALIASES = [
        'job_title', 'job title', 'recommended_career', 'recommended career',
        'career', 'occupation', 'role', 'position', 'job_role',
    ]

    # Stage 1: exact alias match (case-insensitive)
    source_col = None
    col_lower_map = {c.lower(): c for c in df.columns}
    for alias in JOB_TITLE_ALIASES:
        if alias.lower() in col_lower_map:
            source_col = col_lower_map[alias.lower()]
            break

    # Stage 2: keyword fuzzy match on column name
    if source_col is None:
        keywords = ['job', 'career', 'occupation', 'role', 'position', 'recommended']
        for col in df.columns:
            if any(kw in col.lower() for kw in keywords):
                source_col = col
                break

    if source_col is None:
        if verbose:
            print("  No job/career column found - skipping")
        return df

    if verbose:
        print(f"  Using column '{source_col}' for job title standardisation")

    df['job_title_original'] = df[source_col].fillna('Unknown')

    titles = (
        df[source_col]
        .fillna('Unknown')
        .astype(str)
        .str.lower()
        .str.strip()
        .str.replace(r'[^\w\s]', ' ', regex=True)  # commas/punctuation -> space handles "Engineer, chemical"
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )

    def normalize(title):
        for pattern, replacement in JOB_TITLE_PATTERNS.items():
            if re.search(pattern, title):
                return replacement
        return "Other"

    df['job_title_clean'] = titles.apply(normalize)
    return df


# 5 Map career family with fallback on original titles

def map_career_family(df):
    """

    Layer 1 (unchanged): regex pattern match -> standardised title -> CAREER_FAMILY_MAP
    Layer 2 (unchanged): keyword fallback on original title string
    Layer 3 (NEW):       fuzzy string match against already-classified titles
                         to catch abbreviations/typos that layers 1-2 miss.
                         
    """
    df = df.copy()
    if 'job_title_clean' not in df.columns:
        return df

    # Layer 1: direct map from standardised title
    df['career_family'] = df['job_title_clean'].map(CAREER_FAMILY_MAP)

    # Layer 2: keyword fallback on the original raw title
    mask = df['career_family'].isna() | (df['career_family'] == 'Other')
    if mask.any():
        df.loc[mask, 'career_family'] = df.loc[mask, 'job_title_original'].apply(assign_fallback_family)

    # FIX Issue 3 — Layer 3: fuzzy match any remaining 'Other' titles
    # against the pool of titles that were successfully classified.
    mask = df['career_family'].isna() | (df['career_family'] == 'Other')
    if mask.any():
        try:
            from thefuzz import process as fuzz_process
            classified_titles = df.loc[~mask, 'job_title_original'].unique().tolist()
            family_lookup = df.loc[~mask].set_index('job_title_original')['career_family'].to_dict()

            def fuzzy_rescue(title):
                if not classified_titles:
                    return 'Other'
                match, score = fuzz_process.extractOne(str(title), classified_titles)
                if score >= 75:   # threshold: lower = more lenient
                    return family_lookup.get(match, 'Other')
                return 'Other'

            df.loc[mask, 'career_family'] = (
                df.loc[mask, 'job_title_original'].apply(fuzzy_rescue)
            )
        except ImportError:
            
            pass

    df['career_family'] = df['career_family'].fillna('Other')
    return df


# 6 Apply to all datasets

def standardize_all_jobs(cleaned_storage, verbose=True):
    for key, df in cleaned_storage.items():
        if verbose:
            print(f"\n[{key}]")
        df = standardize_job_title(df, verbose=verbose)
        df = map_career_family(df)
        cleaned_storage[key] = df
        if 'career_family' in df.columns:
            other_pct = (df['career_family'] == 'Other').mean() * 100
            print(f"  Done - 'Other' family: {other_pct:.1f}%")
    return cleaned_storage