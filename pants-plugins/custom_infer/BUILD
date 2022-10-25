pants_requirement(name="pants", dist="pantsbuild.pants")
pants_requirement(name="pants.testutil", dist="pantsbuild.pants.testutil")

python_sources()

python_tests(
    name="tests",
    dependencies=[
        ":custom_infer",
        ":pants",
        ":pants.testutil"
    ]
)
