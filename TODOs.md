1. Refactor Resource Management: Move HTML templates and other static assets into a dedicated `resource` or `resources` directory. Update the `get_resource` function and related code to resolve paths within these directories.
2. Enhance Market Report Classification: Update the reporting logic to explicitly classify opportunities based on asset size and price:
   - **Shorting**: Focus on short position opportunities (small assets, expensive price).
   - **Longing**: Focus on long position opportunities (large assets, cheap price).