"""
Direct test of the v2 dissertation generator -- bypasses the API entirely.
Runs the generator in-process so we see all output and errors immediately.
"""
import asyncio
import logging
import sys
import io
import os
import time

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Set up logging to see everything
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Ensure we can import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from src.ai.dissertation_generator_v2 import generate_dissertation

    topic = "Deep Learning for Early Cancer Detection: CNN vs Transformer Architectures"
    description = (
        "This dissertation critically evaluates CNN and vision transformer "
        "architectures for automated cancer detection in chest X-ray and CT "
        "imaging. It challenges the prevailing assumption that larger models "
        "inherently produce more clinically reliable predictions."
    )
    discipline = "stem"

    print("=" * 60, file=sys.stderr)
    print("STARTING DIRECT V2 GENERATION TEST", file=sys.stderr)
    print(f"Topic: {topic}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    start = time.time()
    
    try:
        result = await generate_dissertation(
            topic=topic,
            description=description,
            discipline=discipline,
        )
    except Exception as exc:
        print(f"\nFATAL ERROR: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - start
    mins = int(elapsed) // 60
    secs = int(elapsed) % 60

    print("\n" + "=" * 60, file=sys.stderr)
    print("GENERATION COMPLETE", file=sys.stderr)
    print(f"Time: {mins}m {secs}s", file=sys.stderr)
    print(f"Total words: {result.total_words:,}", file=sys.stderr)
    print(f"Total papers: {result.total_papers}", file=sys.stderr)
    print(f"Verified citations: {result.verified_citations}", file=sys.stderr)
    print(f"Hallucinated citations: {result.hallucinated_citations}", file=sys.stderr)
    print(f"Student-input sections: {len(result.student_input_sections)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    for section in result.sections:
        student_markers = section.content.count("<!-- STUDENT:")
        mode_str = section.mode.value if hasattr(section.mode, 'value') else str(section.mode)
        marker_text = f" [{student_markers} student markers]" if student_markers else ""
        print(f"  {section.title}: {section.word_count:,} words ({mode_str}){marker_text}", file=sys.stderr)
        for sub in section.subsections:
            v = sub.verified_citations
            h = sub.hallucinated_citations
            cite_text = f" [citations: {v} verified, {h} hallucinated]" if v + h > 0 else ""
            print(f"    - {sub.title}: {sub.word_count:,} words{cite_text}", file=sys.stderr)

    print(f"\nTOTAL: {result.total_words:,} words", file=sys.stderr)
    print("DONE", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
