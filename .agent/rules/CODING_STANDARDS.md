---
trigger: always_on
---

# Python 架构与代码规范指南

## 1. 基础构建块
* 类型检查： 领域层代码必须 100% 包含 Type Hints（类型提示）。
* 类定义： 优先使用 Python 标准库的 @dataclass 或第三方库 Pydantic (BaseModel) 来定义领域对象。
* ORM 隔离： 领域模型绝对不能继承自 sqlalchemy.Model、django.db.models.Model 等任何 ORM 基类。

## 2. 实体 (Entity) 规范
* 使用 @dataclass(eq=False) 声明。
* 必须手动实现 __eq__ 和 __hash__，并且仅通过唯一标识符（如 id 或 uuid）来判断实体是否相等。
* 业务校验规则必须放置在 __post_init__ 魔术方法中，或者在 Pydantic 的 @field_validator 中，确保对象一旦创建即是合法状态。

## 3. 值对象 (Value Object) 规范
* 必须使用 @dataclass(frozen=True) 声明，保证其不可变性。尝试修改值对象的属性必须在运行时引发异常。
* 对于金额、地址、坐标等概念，必须封装为值对象，严禁在领域实体中直接散落 latitude: float, longitude: float 这样的原生类型字段。