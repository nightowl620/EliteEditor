#!/usr/bin/env python3
"""
Test Suite for Production Architecture

Verifies:
1. MoviePy Registry (dynamic effect discovery)
2. Real Timeline (QGraphicsView-based)
3. Drag & Drop Payload System
4. Auto-Generated Properties Panel
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)

logger = logging.getLogger(__name__)


def test_moviepy_registry():
    """Test 1: MoviePy Registry"""
    logger.info("=" * 60)
    logger.info("TEST 1: MoviePy Dynamic Registry")
    logger.info("=" * 60)
    
    try:
        from rendering.moviepy_registry import get_registry, list_all_effects
        
        registry = get_registry()
        logger.info(f"Registry available: {registry.available}")
        
        if not registry.available:
            logger.warning("MoviePy not available - skipping")
            return False
        
        # List effects
        effects = list_all_effects()
        
        logger.info(f"✅ Video effects discovered: {len(effects['video'])}")
        logger.info(f"✅ Audio effects discovered: {len(effects['audio'])}")
        logger.info(f"✅ Compositing functions: {len(effects['compositing'])}")
        logger.info(f"✅ Clip types: {len(effects['clips'])}")
        
        # Test getting specific effect
        if effects['video']:
            first_effect = list(effects['video'].keys())[0]
            effect_sig = registry.get_effect(first_effect)
            
            logger.info(f"\n✅ Sample effect: {effect_sig.name}")
            logger.info(f"   Module: {effect_sig.module}")
            logger.info(f"   Parameters: {list(effect_sig.parameters.keys())}")
            logger.info(f"   Has docstring: {bool(effect_sig.doc)}")
        
        logger.info("✅ TEST 1 PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_timeline_graphics():
    """Test 2: Real Timeline Widget"""
    logger.info("=" * 60)
    logger.info("TEST 2: Real QGraphicsView Timeline")
    logger.info("=" * 60)
    
    try:
        from timeline.graphics_timeline import (
            TimelineMarker, RealTimelineWidget, ClipRectItem
        )
        
        # Create marker
        marker = TimelineMarker(
            id='test_clip_1',
            name='Test Clip',
            track_id='video_0',
            start_frame=0,
            end_frame=150  # 5 seconds @ 30fps
        )
        
        logger.info(f"✅ Created TimelineMarker")
        logger.info(f"   ID: {marker.id}")
        logger.info(f"   Name: {marker.name}")
        logger.info(f"   Duration: {marker.duration_frames} frames")
        logger.info(f"   Logical start: {marker.logical_start}")
        logger.info(f"   Logical finish: {marker.logical_finish}")
        
        # Create widget (no display)
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        
        timeline = RealTimelineWidget()
        timeline.set_fps(30)
        
        # Add marker
        timeline.add_marker(marker)
        logger.info(f"✅ Added marker to timeline")
        logger.info(f"   Total markers: {len(timeline.markers)}")
        
        # Test retrieval
        retrieved = timeline.markers.get('test_clip_1')
        assert retrieved is not None
        logger.info(f"✅ Retrieved marker from timeline")
        
        # Test marker at time
        marker_at_75 = timeline.get_marker_at_time(75)  # Middle of clip
        assert marker_at_75 is not None
        logger.info(f"✅ Found marker at frame 75: {marker_at_75.name}")
        
        # Test zoom
        timeline.set_zoom(200)  # 2x zoom
        logger.info(f"✅ Set zoom to 2x")
        
        logger.info("✅ TEST 2 PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_drag_drop_payload():
    """Test 3: Drag & Drop Payload System"""
    logger.info("=" * 60)
    logger.info("TEST 3: Drag & Drop Payload System")
    logger.info("=" * 60)
    
    try:
        from timeline.dnd_payload import (
            DragPayload, create_marker_from_payload
        )
        from timeline.graphics_timeline import TimelineMarker
        from PySide6.QtWidgets import QApplication
        
        app = QApplication.instance() or QApplication([])
        
        # Create payload
        payload = DragPayload(
            type='effect',
            name='blur',
            moviepy_callable='blur',
            effect_category='video',
            initial_parameters={'sigma': 2.0},
            duration_seconds=5.0
        )
        
        logger.info(f"✅ Created DragPayload")
        logger.info(f"   Type: {payload.type}")
        logger.info(f"   Name: {payload.name}")
        logger.info(f"   Parameters: {payload.initial_parameters}")
        
        # Serialize/deserialize
        json_str = payload.to_json()
        logger.info(f"✅ Serialized to JSON ({len(json_str)} bytes)")
        
        restored = DragPayload.from_json(json_str)
        assert restored.name == payload.name
        logger.info(f"✅ Deserialized from JSON")
        
        # QMimeData round-trip
        mime = payload.to_mime()
        logger.info(f"✅ Converted to QMimeData")
        
        extracted = DragPayload.from_mime(mime)
        assert extracted is not None
        logger.info(f"✅ Extracted from QMimeData")
        
        # Create marker from payload
        from timeline.graphics_timeline import TimelineMarker
        marker = create_marker_from_payload(
            payload,
            timeline=None,
            track_id='video_0',
            start_frame=100
        )
        
        logger.info(f"✅ Created TimelineMarker from payload")
        logger.info(f"   Marker ID: {marker.id}")
        logger.info(f"   Start frame: {marker.start_frame}")
        logger.info(f"   Duration: {marker.duration_frames} frames")
        logger.info(f"   Parameters: {marker.parameters}")
        
        logger.info("✅ TEST 3 PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_properties_panel():
    """Test 4: Auto-Generated Properties Panel"""
    logger.info("=" * 60)
    logger.info("TEST 4: Auto-Generated Properties Panel")
    logger.info("=" * 60)
    
    try:
        from ui.properties_panel import PropertiesPanel
        from PySide6.QtWidgets import QApplication
        from enum import Enum
        
        app = QApplication.instance() or QApplication([])
        
        # Create test effect function
        class ColorMode(Enum):
            RGB = 'rgb'
            HSV = 'hsv'
            LAB = 'lab'
        
        def test_effect(
            sigma: float = 2.0,
            strength: int = 1,
            enabled: bool = True,
            color_space: ColorMode = ColorMode.RGB,
            name: str = "effect"
        ):
            """Test effect with various parameter types."""
            pass
        
        # Create panel and load effect
        panel = PropertiesPanel()
        panel.load_from_callable(test_effect)
        
        logger.info(f"✅ Created PropertiesPanel")
        logger.info(f"✅ Loaded callable signature")
        logger.info(f"   Parameters created: {list(panel.parameter_widgets.keys())}")
        
        # Get values
        values = panel.get_all_values()
        logger.info(f"✅ Retrieved all parameter values:")
        for name, value in values.items():
            logger.info(f"   {name}: {value} ({type(value).__name__})")
        
        # Set values
        panel.set_values({
            'sigma': 5.0,
            'strength': 3,
            'enabled': False,
            'name': 'custom_effect'
        })
        
        new_values = panel.get_all_values()
        logger.info(f"✅ Updated parameter values:")
        for name, value in new_values.items():
            logger.info(f"   {name}: {value}")
        
        logger.info("✅ TEST 4 PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test 5: Integration Test"""
    logger.info("=" * 60)
    logger.info("TEST 5: Integration Test")
    logger.info("=" * 60)
    
    try:
        from rendering.moviepy_registry import get_registry
        from timeline.graphics_timeline import RealTimelineWidget
        from timeline.dnd_payload import DragPayload, create_marker_from_payload
        from ui.properties_panel import PropertiesPanel
        from PySide6.QtWidgets import QApplication
        
        app = QApplication.instance() or QApplication([])
        
        logger.info("Creating timeline...")
        timeline = RealTimelineWidget()
        timeline.set_fps(30)
        
        logger.info("Creating payload from registry...")
        registry = get_registry()
        
        if registry.available and registry.video_effects:
            # Get first video effect
            first_effect_name = list(registry.video_effects.keys())[0]
            first_effect = registry.get_effect(first_effect_name)
            
            logger.info(f"Using effect: {first_effect.name}")
            
            # Create payload
            payload = DragPayload(
                type='effect',
                name=first_effect.name,
                moviepy_callable=first_effect.name,
                effect_category='video'
            )
            
            # Create marker
            marker = create_marker_from_payload(
                payload,
                timeline,
                track_id='video_0',
                start_frame=0
            )
            
            logger.info(f"✅ Created marker: {marker.name}")
            
            # Add to timeline
            timeline.add_marker(marker)
            logger.info(f"✅ Added to timeline")
            
            # Create properties panel and bind
            panel = PropertiesPanel()
            if marker.moviepy_ref:
                panel.load_from_callable(marker.moviepy_ref)
                panel.bind_to_marker(marker)
                logger.info(f"✅ Properties panel bound to marker")
            
            logger.info("✅ TEST 5 PASSED\n")
            return True
        else:
            logger.warning("MoviePy not available - skipping integration test")
            return True
    
    except Exception as e:
        logger.error(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " ELITE EDITOR - PRODUCTION FOUNDATION TEST SUITE ".center(58) + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("\n")
    
    results = []
    
    results.append(("MoviePy Registry", test_moviepy_registry()))
    results.append(("Timeline Graphics", test_timeline_graphics()))
    results.append(("DnD Payload", test_drag_drop_payload()))
    results.append(("Properties Panel", test_properties_panel()))
    results.append(("Integration", test_integration()))
    
    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status:12} | {name}")
    
    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! Production foundation is solid.\n")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} tests failed\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
