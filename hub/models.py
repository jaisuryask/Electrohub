from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=8, default="⚡")
    blurb = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    DIFFICULTY = [("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")]

    title = models.CharField(max_length=140)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="projects")
    board = models.CharField(max_length=60, help_text="e.g. ESP32, Arduino Uno")
    summary = models.CharField(max_length=240)
    description = models.TextField()
    difficulty = models.CharField(max_length=12, choices=DIFFICULTY, default="beginner")
    build_minutes = models.PositiveIntegerField(default=30)
    cost_usd = models.PositiveIntegerField(default=15)
    tags = models.CharField(max_length=200, blank=True, help_text="comma separated")
    youtube_id = models.CharField(max_length=20, blank=True)
    video_credit = models.CharField(max_length=140, blank=True)
    image_url = models.URLField(blank=True, help_text="Optional hero image; falls back to video thumbnail")
    safety_note = models.CharField(max_length=300, blank=True)
    featured = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-featured", "-created"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("project", args=[self.slug])

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def thumbnail(self):
        if self.image_url:
            return self.image_url
        if self.youtube_id:
            return f"https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg"
        return ""


class Component(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="components")
    name = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField(default=1)
    note = models.CharField(max_length=160, blank=True)

    def __str__(self):
        return f"{self.quantity}× {self.name}"


class Connection(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="connections")
    order = models.PositiveIntegerField(default=0)
    from_part = models.CharField(max_length=60)
    from_pin = models.CharField(max_length=30)
    to_part = models.CharField(max_length=60)
    to_pin = models.CharField(max_length=30)
    wire_color = models.CharField(max_length=9, default="#22d3ee")
    note = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["order", "id"]


class CodeFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="code_files")
    order = models.PositiveIntegerField(default=0)
    filename = models.CharField(max_length=80)
    language = models.CharField(max_length=20, default="cpp")
    description = models.CharField(max_length=200, blank=True)
    content = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.project.slug}/{self.filename}"


class Step(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=120)
    body = models.TextField()

    class Meta:
        ordering = ["order", "id"]


class FAQ(models.Model):
    question = models.CharField(max_length=200)
    answer = models.TextField()
    category = models.CharField(max_length=40, default="General")
    keywords = models.CharField(max_length=200, blank=True, help_text="extra search words, comma separated")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category", "order", "id"]
        verbose_name = "FAQ"

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    code = models.CharField(max_length=12, unique=True, help_text="HTTP status (404) or site code (EL-1001)")
    title = models.CharField(max_length=80)
    meaning = models.TextField()
    fix = models.TextField()
    http_status = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.title}"


class Ticket(models.Model):
    STATUS = [("open", "Open"), ("in_progress", "In progress"), ("closed", "Closed")]
    question = models.TextField()
    email = models.EmailField(blank=True)
    source = models.CharField(max_length=20, default="chat")
    session_id = models.CharField(max_length=64, blank=True)
    page = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="open")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    @property
    def ref(self):
        return f"ELT-{self.pk:04d}"

    def __str__(self):
        return f"{self.ref}: {self.question[:50]}"


class AIQuery(models.Model):
    """Lightweight log of AI usage (shown in admin; helps tune the knowledge base)."""

    kind = models.CharField(max_length=20)
    prompt = models.TextField()
    engine = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
