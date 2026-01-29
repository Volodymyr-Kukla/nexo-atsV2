from candidates.models import Candidate, CandidateExperience, Skill
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from pipeline.models import Application, Stage
from projects.models import Project


class Command(BaseCommand):
    help = "Seed demo data for ATS (projects, candidates, pipeline)"

    def handle(self, *args, **options):
        User = get_user_model()
        owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not owner:
            self.stderr.write("No users found. Create a superuser first.")
            return

        # --- Projects (для прикладу як на скрінах) ---
        projects_data = [
            {
                "title": "Frontend Developer",
                "description": "Розробка сучасного веб-додатку з використанням React та TypeScript",
                "location": "Київ, Україна",
                "is_remote": True,
                "department": "IT відділ",
                "status": Project.Status.IN_PROGRESS,
            },
            {
                "title": "Водій Львів",
                "description": "Пошук водія для логістичних задач",
                "location": "Львів, Україна",
                "is_remote": False,
                "department": "Операційний відділ",
                "status": Project.Status.IN_PROGRESS,
            },
            {
                "title": "Менеджер з продажу",
                "description": "B2B продажі та ведення клієнтів",
                "location": "Одеса, Україна",
                "is_remote": False,
                "department": "Sales",
                "status": Project.Status.PENDING,
            },
            {
                "title": "HR Менеджер",
                "description": "Закрита вакансія для прикладу",
                "location": "Харків, Україна",
                "is_remote": False,
                "department": "HR",
                "status": Project.Status.CLOSED,
            },
        ]

        created_projects = []
        for p in projects_data:
            project, _ = Project.objects.get_or_create(
                title=p["title"],
                defaults={
                    "description": p["description"],
                    "location": p["location"],
                    "is_remote": p["is_remote"],
                    "department": p["department"],
                    "status": p["status"],
                    "owner": owner,
                },
            )
            created_projects.append(project)

        main_project = Project.objects.get(title="Frontend Developer")

        # ensure stages exist (на випадок якщо проєкт був створений до сигналів)
        if not Stage.objects.filter(project=main_project).exists():
            self.stderr.write(
                "No stages found for main project. Recreate project or check signals."
            )
            return

        stage_new = Stage.objects.get(project=main_project, system_key="new")
        stage_screen = Stage.objects.get(project=main_project, system_key="screening")
        stage_interview = Stage.objects.get(project=main_project, system_key="interview")

        # --- Skills ---
        skill_names = [
            "React",
            "TypeScript",
            "Next.js",
            "Node.js",
            "GraphQL",
            "Tailwind CSS",
            "Git",
            "REST API",
            "Redux",
            "Jest",
        ]
        skills = {}
        for name in skill_names:
            obj, _ = Skill.objects.get_or_create(name=name)
            skills[name] = obj

        # --- Candidates (як у прикладах) ---
        candidates_data = [
            {
                "first_name": "Марія",
                "last_name": "Коваленко",
                "email": "maria.k@example.com",
                "phone": "+380671234567",
                "city": "Київ",
                "experience_years": 3,
                "rating": 4,
                "about": "Frontend Developer з досвідом у React/TS/Next.js. Командна робота, оптимізація продуктивності.",
                "skills": [
                    "React",
                    "TypeScript",
                    "Next.js",
                    "Tailwind CSS",
                    "Git",
                    "REST API",
                    "Redux",
                    "Jest",
                ],
                "stage": stage_new,
                "experiences": [
                    {
                        "title": "Senior Frontend Developer",
                        "company": "TechCorp Inc.",
                        "description": "Розробка enterprise-рішень, координація 4 розробників.",
                        "order": 1,
                    },
                    {
                        "title": "Frontend Developer",
                        "company": "StartupHub",
                        "description": "SaaS-платформа, впровадження CI/CD, підтримка компонентної системи.",
                        "order": 2,
                    },
                ],
            },
            {
                "first_name": "Олександр",
                "last_name": "Шевченко",
                "email": "alex.s@example.com",
                "phone": "+380674567890",
                "city": "Київ",
                "experience_years": 4,
                "rating": 5,
                "about": "Frontend Developer, focus: performance, DX, архітектура UI.",
                "skills": ["React", "TypeScript", "GraphQL", "Tailwind CSS", "Git", "REST API"],
                "stage": stage_screen,
                "experiences": [
                    {
                        "title": "Frontend Developer",
                        "company": "ProductTeam",
                        "description": "Компонентна бібліотека, інтеграції, оптимізації.",
                        "order": 1,
                    }
                ],
            },
            {
                "first_name": "Іван",
                "last_name": "Петренко",
                "email": "ivan.p@example.com",
                "phone": "+380676789012",
                "city": "Київ",
                "experience_years": 5,
                "rating": 4,
                "about": "Full-stack oriented frontend, сильний у state management.",
                "skills": ["React", "TypeScript", "Next.js", "Redux", "Git", "REST API"],
                "stage": stage_interview,
                "experiences": [
                    {
                        "title": "Frontend Developer",
                        "company": "Enterprise UA",
                        "description": "Складні форми, таблиці, інтеграції з REST.",
                        "order": 1,
                    }
                ],
            },
        ]

        for c in candidates_data:
            candidate, created = Candidate.objects.get_or_create(
                email=c["email"],
                defaults={
                    "first_name": c["first_name"],
                    "last_name": c["last_name"],
                    "phone": c["phone"],
                    "city": c["city"],
                    "experience_years": c["experience_years"],
                    "rating": c["rating"],
                    "about": c["about"],
                },
            )

            # sync base fields якщо вже існує
            if not created:
                candidate.first_name = c["first_name"]
                candidate.last_name = c["last_name"]
                candidate.phone = c["phone"]
                candidate.city = c["city"]
                candidate.experience_years = c["experience_years"]
                candidate.rating = c["rating"]
                candidate.about = c["about"]
                candidate.save()

            # skills
            candidate.skills.clear()
            for s in c["skills"]:
                candidate.skills.add(skills[s])

            # experiences (проста стратегія: очистити й перезалити)
            candidate.experiences.all().delete()
            for e in c["experiences"]:
                CandidateExperience.objects.create(
                    candidate=candidate,
                    title=e["title"],
                    company=e["company"],
                    description=e["description"],
                    order=e.get("order", 0),
                )

            # application into main project
            app, _ = Application.objects.get_or_create(
                project=main_project,
                candidate=candidate,
                defaults={"current_stage": c["stage"], "position_in_stage": 0},
            )
            # якщо вже є — оновити stage
            if app.current_stage_id != c["stage"].id:
                app.current_stage = c["stage"]
                app.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete: projects, candidates, stages, applications created/updated."
            )
        )
