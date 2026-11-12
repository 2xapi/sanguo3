#!/usr/bin/env python3
"""Compare PNG pixels exactly. No resizing, masks, thresholds or baseline updates."""
from pathlib import Path
import argparse
import hashlib
import json
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--actual', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        from PIL import Image
    except ImportError:
        print('Pillow is required. See the pinned tools/requirements.txt.', file=sys.stderr)
        return 2

    try:
        reference = args.reference.resolve(strict=True)
        actual = args.actual.resolve(strict=True)
        if reference == actual or reference.samefile(actual):
            raise ValueError('Reference and actual must be distinct files, not self-comparison.')
        imgs = []
        metadata = []
        for path in [reference, actual]:
            with Image.open(path) as image:
                image.load()
                if image.format != 'PNG':
                    raise ValueError('Only PNG inputs are accepted. Preserve raw references separately.')
                if path.read_bytes()[24] not in {1, 2, 4, 8}:
                    raise ValueError('Unsupported PNG bit depth; no silent bit-depth reduction.')
                if image.mode not in {'1', 'L', 'LA', 'P', 'RGB', 'RGBA'}:
                    raise ValueError(f'Unsupported pixel mode {image.mode}; no silent bit-depth reduction.')
                if getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Animated PNG must be sampled to a documented frame first.')
                metadata.append(tuple(image.info.get(k) for k in ['icc_profile', 'gamma', 'srgb', 'chromaticity']))
                imgs.append(image.convert('RGBA'))
        if metadata[0] != metadata[1]:
            raise ValueError('Color metadata differ. Establish a documented normalization first; no automatic color correction.')
        ref, act = imgs
        if ref.size != act.size:
            raise ValueError(f'Size mismatch: {ref.size} != {act.size}. No resizing is allowed.')

        mask_values = []
        diff_count = max_diff = 0
        for rp, ap in zip(ref.getdata(), act.getdata()):
            d = max(abs(a - b) for a, b in zip(rp, ap))
            diff_count += d != 0
            max_diff = max(max_diff, d)
            mask_values.append(255 if d else 0)
        mask = Image.new('L', ref.size)
        mask.putdata(mask_values)
        bbox = mask.getbbox()
        out = args.out.resolve()
        names = ['comparison-report.json', 'comparison-diff.png', 'comparison-overlay.png', 'comparison-side-by-side.png']
        for name in names:
            dest = out / name
            if dest.exists() or dest.resolve() in {reference, actual}:
                raise ValueError(f'Refusing to overwrite: {dest}. Choose a fresh output directory.')
        out.mkdir(parents=True, exist_ok=True)

        # Visualizations use a black preview background; comparisons use all raw RGBA channels.
        def preview(im):
            bg = Image.new('RGBA', im.size, (0, 0, 0, 255))
            return Image.alpha_composite(bg, im).convert('RGB')

        rp, ap = preview(ref), preview(act)
        diff = Image.new('RGB', ref.size, 'black')
        diff.paste(Image.new('RGB', ref.size, '#ff253a'), mask=mask)
        overlay = Image.blend(rp, ap, 0.5)
        side = Image.new('RGB', (ref.width * 2, ref.height))
        side.paste(rp, (0, 0))
        side.paste(ap, (ref.width, 0))
        diff.save(out / names[1])
        overlay.save(out / names[2])
        side.save(out / names[3])
        report = {
            'result': 'passed' if diff_count == 0 else 'failed',
            'comparison': 'exact decoded RGBA; no color transforms, resampling, masks or thresholds',
            'reference': {'path': str(reference), 'sha256': hashlib.sha256(reference.read_bytes()).hexdigest()},
            'actual': {'path': str(actual), 'sha256': hashlib.sha256(actual.read_bytes()).hexdigest()},
            'width': ref.width, 'height': ref.height, 'diffPixels': diff_count,
            'maxChannelDifference': max_diff, 'differenceBoundingBoxExclusive': bbox,
            'referenceAuthenticityVerified': False,
            'sceneAndTimingMatchVerified': False,
            'notes': 'Zero difference proves these decoded inputs match, not original-game authenticity or complete-game coverage.'
        }
        (out / names[0]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'result': report['result'], 'diffPixels': diff_count, 'maxChannelDifference': max_diff, 'bbox': bbox, 'report': str(out / names[0])}))
        return 0 if diff_count == 0 else 1
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        print('INPUT ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
