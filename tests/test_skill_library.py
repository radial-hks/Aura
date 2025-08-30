"""技能库测试"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.modules.skill_library import (
    SkillLibrary, SkillManifest, SkillStatus, SkillInput, SkillOutput, 
    SkillAssertion, SkillExample, SkillSignature, ExecutionResult
)
from src.utils.exceptions import ValidationError, SkillExecutionError, ResourceNotFoundError


class TestSkillLibrary:
    """技能库测试类"""

    def test_register_skill_success(self, skill_library, sample_skill_manifest, temp_dir):
        """测试成功注册技能"""
        # 创建技能目录和脚本文件
        skill_dir = temp_dir / sample_skill_manifest.id
        skill_dir.mkdir()
        
        script_content = '''
const { chromium } = require('playwright');

async function executeSkill(params) {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    try {
        await page.goto('https://example.com');
        await page.fill('input[name="q"]', params.query);
        await page.click('button[type="submit"]');
        
        const results = await page.$$eval('.result', els => 
            els.map(el => el.textContent)
        );
        
        return { success: true, results };
    } finally {
        await browser.close();
    }
}

module.exports = { executeSkill };
'''
        
        # 写入脚本文件
        (skill_dir / "script.js").write_text(script_content)
        
        result = skill_library.register_skill(
            manifest=sample_skill_manifest,
            skill_path=skill_dir
        )
        
        assert result is True
        assert sample_skill_manifest.id in skill_library.skills
        assert skill_library.skills[sample_skill_manifest.id].status == SkillStatus.ACTIVE

    def test_register_skill_invalid_manifest(self, skill_library, temp_dir):
        """测试注册无效清单的技能"""
        # 创建无效的SkillManifest对象（缺少必需字段）
        invalid_manifest = SkillManifest(
            id="",  # 空ID
            name="Invalid Skill",
            version="1.0.0",
            description="Test skill",
            author="test"
        )
        
        skill_dir = temp_dir / "invalid_skill"
        skill_dir.mkdir()
        (skill_dir / "script.js").write_text("console.log('test');")
        
        result = skill_library.register_skill(
            manifest=invalid_manifest,
            skill_path=skill_dir
        )
        
        assert result is False  # 注册应该失败

    def test_register_skill_duplicate_id(self, skill_library, sample_skill_manifest, temp_dir):
        """测试注册重复ID的技能"""
        # 首次注册
        skill_dir1 = temp_dir / sample_skill_manifest.id
        skill_dir1.mkdir()
        (skill_dir1 / "script.js").write_text("console.log('test');")
        
        result1 = skill_library.register_skill(
            manifest=sample_skill_manifest,
            skill_path=skill_dir1
        )
        assert result1 is True
        
        # 尝试再次注册相同ID但版本相同
        skill_dir2 = temp_dir / f"{sample_skill_manifest.id}_v2"
        skill_dir2.mkdir()
        (skill_dir2 / "script.js").write_text("console.log('test2');")
        
        result2 = skill_library.register_skill(
            manifest=sample_skill_manifest,  # 相同版本
            skill_path=skill_dir2
        )
        assert result2 is False  # 应该失败，因为版本不是更新的

    def test_update_skill_success(self, skill_library, sample_skill_manifest, temp_dir):
        """测试成功更新技能"""
        # 注册初始版本
        skill_dir1 = temp_dir / sample_skill_manifest.id
        skill_dir1.mkdir()
        (skill_dir1 / "script.js").write_text("console.log('v1');")
        
        result1 = skill_library.register_skill(
            manifest=sample_skill_manifest,
            skill_path=skill_dir1
        )
        assert result1 is True
        
        # 创建更新版本的manifest
        from dataclasses import replace
        updated_manifest = replace(
            sample_skill_manifest,
            version='1.1.0',
            description='Updated description'
        )
        
        skill_dir2 = temp_dir / f"{sample_skill_manifest.id}_v2"
        skill_dir2.mkdir()
        (skill_dir2 / "script.js").write_text("console.log('v1.1');")
        
        result2 = skill_library.register_skill(
            manifest=updated_manifest,
            skill_path=skill_dir2
        )
        
        assert result2 is True
        
        # 验证更新
        updated_skill = skill_library.skills[sample_skill_manifest.id]
        assert updated_skill.version == '1.1.0'
        assert updated_skill.description == 'Updated description'

    def test_get_skill_success(self, skill_library, sample_skill_manifest, temp_dir):
        """测试成功获取技能"""
        skill_dir = temp_dir / sample_skill_manifest.id
        skill_dir.mkdir()
        (skill_dir / "script.js").write_text("console.log('test');")
        
        result = skill_library.register_skill(
            manifest=sample_skill_manifest,
            skill_path=skill_dir
        )
        assert result is True
        
        # 直接从skills字典获取技能信息
        skill_info = skill_library.skills[sample_skill_manifest.id]
        
        assert skill_info.id == sample_skill_manifest.id
        assert skill_info.name == sample_skill_manifest.name
        assert skill_info.status == SkillStatus.ACTIVE
        assert skill_info.created_at is not None
        assert skill_info.updated_at is not None

    def test_get_skill_not_found(self, skill_library):
        """测试获取不存在的技能"""
        # 直接检查技能是否存在于skills字典中
        assert "nonexistent.skill" not in skill_library.skills

    def test_search_skills_by_name(self, skill_library, sample_skill_manifest, temp_dir):
        """测试按名称搜索技能"""
        # 注册几个技能
        from dataclasses import replace
        
        skill1 = replace(sample_skill_manifest, id='search.skill1', name='Search Products')
        skill2 = replace(sample_skill_manifest, id='login.skill1', name='User Login')
        
        # 注册第一个技能
        skill_dir1 = temp_dir / skill1.id
        skill_dir1.mkdir()
        (skill_dir1 / "script.js").write_text("console.log('search');")
        skill_library.register_skill(skill1, skill_dir1)
        
        # 注册第二个技能
        skill_dir2 = temp_dir / skill2.id
        skill_dir2.mkdir()
        (skill_dir2 / "script.js").write_text("console.log('login');")
        skill_library.register_skill(skill2, skill_dir2)
        
        # 使用find_skills方法搜索
        results = skill_library.find_skills(query="search")
        
        assert len(results) >= 1
        assert any(skill.name == 'Search Products' for skill in results)

    def test_search_skills_by_target(self, skill_library, sample_skill_manifest, temp_dir):
        """测试按目标域名搜索技能"""
        # 注册针对不同网站的技能
        from dataclasses import replace
        
        skill1 = replace(sample_skill_manifest, id='amazon.search', target_domains=['amazon.com'])
        skill2 = replace(sample_skill_manifest, id='google.search', target_domains=['google.com'])
        
        # 注册第一个技能
        skill_dir1 = temp_dir / skill1.id
        skill_dir1.mkdir()
        (skill_dir1 / "script.js").write_text("console.log('amazon');")
        skill_library.register_skill(skill1, skill_dir1)
        
        # 注册第二个技能
        skill_dir2 = temp_dir / skill2.id
        skill_dir2.mkdir()
        (skill_dir2 / "script.js").write_text("console.log('google');")
        skill_library.register_skill(skill2, skill_dir2)
        
        # 搜索Amazon技能
        results = skill_library.find_skills(domain="amazon.com")
        
        assert len(results) >= 1
        assert all('amazon.com' in skill.target_domains for skill in results)

    def test_find_matching_skills(self, skill_library, sample_skill_manifest, temp_dir):
        """测试查找匹配技能"""
        # 注册搜索技能
        skill_dir = temp_dir / sample_skill_manifest.id
        skill_dir.mkdir()
        (skill_dir / "script.js").write_text("console.log('search');")
        
        skill_library.register_skill(
            manifest=sample_skill_manifest,
            skill_path=skill_dir
        )
        
        # 使用find_skills方法查找匹配的技能
        matches = skill_library.find_skills(
            domain="example.com",
            query="search"
        )
        
        assert len(matches) >= 1
        assert matches[0].id == sample_skill_manifest.id

    def test_skill_library_basic_operations(self, skill_library, sample_skill_manifest, temp_dir):
        """测试基本技能库操作"""
        # 注册技能
        skill_dir = temp_dir / sample_skill_manifest.id
        skill_dir.mkdir()
        (skill_dir / "script.js").write_text("console.log('test');")
        
        skill_library.register_skill(
            manifest=sample_skill_manifest,
            skill_path=skill_dir
        )
        
        # 验证技能已注册
        assert sample_skill_manifest.id in skill_library.skills
        skill = skill_library.skills[sample_skill_manifest.id]
        assert skill.name == sample_skill_manifest.name
        assert skill.status == SkillStatus.ACTIVE

    def test_skill_manifest_creation(self, sample_skill_manifest):
        """测试SkillManifest创建"""
        assert sample_skill_manifest.id == 'example.search'
        assert sample_skill_manifest.version == '1.0.0'
        assert sample_skill_manifest.name == 'Example Search'
        assert sample_skill_manifest.target_domains == ['example.com']

    def test_skill_status_enum(self):
        """测试SkillStatus枚举"""
        assert SkillStatus.ACTIVE.value == 'active'
        assert SkillStatus.DEPRECATED.value == 'deprecated'
        assert SkillStatus.DISABLED.value == 'disabled'