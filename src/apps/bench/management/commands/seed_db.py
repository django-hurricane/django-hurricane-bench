import random
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.bench.models import Category, Product


class Command(BaseCommand):
    help = "Seeds database with initial test user and realistic products for benchmarking"

    def add_arguments(self, parser):
        parser.add_argument(
            "--products",
            type=int,
            default=500,
            help="Number of products to generate (default: 500)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force recreation even if data already exists",
        )

    def handle(self, *args, **options):
        num_products = options["products"]
        force = options["force"]

        # 1. Create benchmark user
        user, created = User.objects.get_or_create(username="benchuser")
        if created or force:
            user.set_password("benchpassword")
            user.email = "benchuser@example.com"
            user.save()
            self.stdout.write(self.style.SUCCESS("User 'benchuser' initialized."))

        # 2. Check existing count
        existing_count = Product.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.NOTICE(
                    f"Database already contains {existing_count} products. Skipping seeding (use --force to override)."
                )
            )
            return

        if force:
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed existing products and categories."))

        # 3. Create Categories
        category_data = [
            ("Cloud Compute", "Virtual instances, bare-metal servers, and edge nodes"),
            ("Database Engines", "Managed relational, document, and vector databases"),
            ("Network & CDN", "Load balancers, CDN routing, and low-latency transit"),
            ("Developer Tooling", "CI/CD runners, container registries, and IDE tooling"),
            ("AI & Machine Learning", "GPU accelerators, tensor units, and training clusters"),
            ("Storage & Backup", "NVMe block volumes, object stores, and cold archival"),
            ("Security & Identity", "HSM appliances, IAM governors, and zero-trust proxies"),
            ("Observability & APM", "Distributed tracing agents, metrics collectors, and logging"),
            ("Message Brokers", "Event streams, high-throughput queues, and pub/sub nodes"),
            ("Serverless Functions", "Low-latency event triggers and ephemeral micro-runtimes"),
        ]

        categories = []
        for name, desc in category_data:
            cat, _ = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "description": desc},
            )
            categories.append(cat)

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(categories)} product categories."))

        # 4. Generate Products
        adjectives = ["High-Performance", "Scalable", "Resilient", "Managed", "Enterprise", "Global", "Low-Latency", "Ultra", "Autonomous", "Micro"]
        nouns = ["Cluster", "Gateway", "Engine", "Instance", "Pipeline", "Repository", "Pool", "Accelerator", "Cache", "Mesh"]
        spec_keys = [("ram", ["8GB", "16GB", "32GB", "64GB", "128GB"]),
                     ("vcpus", ["2", "4", "8", "16", "32", "64"]),
                     ("region", ["us-east-1", "eu-central-1", "ap-southeast-1", "sa-east-1"]),
                     ("sla", ["99.9%", "99.95%", "99.99%", "99.999%"])]
        tags_pool = ["cloud", "k8s", "fast", "reliable", "secure", "edge", "ha", "tier-1", "multi-az", "managed"]

        products_to_create = []
        for i in range(1, num_products + 1):
            category = random.choice(categories)
            name = f"{random.choice(adjectives)} {category.name} {random.choice(nouns)} #{i}"
            sku = f"SKU-{category.slug[:3].upper()}-{i:05d}"
            price = Decimal(str(round(random.uniform(9.99, 999.99), 2)))
            stock = random.randint(0, 150)
            rating = round(random.uniform(3.2, 5.0), 2)
            tags = random.sample(tags_pool, k=random.randint(2, 4))
            specifications = {k: random.choice(vals) for k, vals in spec_keys}
            specifications["generation"] = f"Gen-{random.randint(3, 7)}"

            products_to_create.append(
                Product(
                    category=category,
                    sku=sku,
                    name=name,
                    description=f"{name} is engineered for enterprise-grade throughput and strict uptime requirements.",
                    price=price,
                    stock=stock,
                    rating=rating,
                    tags=tags,
                    specifications=specifications,
                    is_active=True,
                )
            )

        Product.objects.bulk_create(products_to_create, batch_size=250)
        self.stdout.write(self.style.SUCCESS(f"Successfully generated {num_products} products in database."))
