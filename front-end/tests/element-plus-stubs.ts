/**
 * Element Plus 测试替身模块。
 * jsdom 下真实 Element Plus 表格和选择器会触发布局测量或递归更新噪声，
 * 这里用轻量组件保留 v-model、slot、点击和表格行渲染行为。
 */

import { computed, defineComponent, h, inject, provide, type ComputedRef, type PropType } from 'vue';

const tableRowsKey = Symbol('tableRows');

/** 常用 Element Plus 组件的轻量 stub 集合。 */
export const elementPlusStubs = {
  ElButton: defineComponent({
    name: 'ElButton',
    emits: ['click'],
    setup(_, { attrs, emit, slots }) {
      /** 将 Element Plus Button 简化成原生 button，并保留 click 事件。 */
      return () =>
        h(
          'button',
          {
            ...attrs,
            type: 'button',
            onClick: (event: MouseEvent) => emit('click', event),
          },
          slots.default?.(),
        );
    },
  }),
  ElCheckbox: defineComponent({
    name: 'ElCheckbox',
    props: {
      modelValue: {
        type: Boolean,
        default: false,
      },
    },
    emits: ['update:modelValue'],
    setup(props, { attrs, emit }) {
      /** 保留 checkbox 的 checked 与 update:modelValue 合约。 */
      return () =>
        h('input', {
          ...attrs,
          checked: props.modelValue,
          type: 'checkbox',
          onChange: (event: Event) => emit('update:modelValue', (event.target as HTMLInputElement).checked),
        });
    },
  }),
  ElDialog: defineComponent({
    name: 'ElDialog',
    props: {
      modelValue: {
        type: Boolean,
        default: false,
      },
      title: {
        type: String,
        default: '',
      },
    },
    emits: ['update:modelValue'],
    setup(props, { slots }) {
      /** 只在 modelValue 为 true 时渲染弹窗内容，模拟 Dialog 显隐行为。 */
      return () =>
        props.modelValue
          ? h('section', { class: 'el-dialog-stub' }, [h('h2', props.title), slots.default?.()])
          : null;
    },
  }),
  ElDropdown: defineComponent({
    name: 'ElDropdown',
    setup(_, { slots }) {
      /** 直接渲染默认插槽和 dropdown 插槽，便于测试点击菜单项。 */
      return () => h('div', { class: 'el-dropdown-stub' }, [slots.default?.(), slots.dropdown?.()]);
    },
  }),
  ElDropdownItem: defineComponent({
    name: 'ElDropdownItem',
    emits: ['click'],
    setup(_, { emit, slots }) {
      return () =>
        h('button', { type: 'button', onClick: (event: MouseEvent) => emit('click', event) }, slots.default?.());
    },
  }),
  ElDropdownMenu: defineComponent({
    name: 'ElDropdownMenu',
    setup(_, { slots }) {
      return () => h('div', { class: 'el-dropdown-menu-stub' }, slots.default?.());
    },
  }),
  ElInput: defineComponent({
    name: 'ElInput',
    props: {
      modelValue: {
        type: String,
        default: '',
      },
      placeholder: {
        type: String,
        default: '',
      },
    },
    emits: ['update:modelValue'],
    setup(props, { attrs, emit }) {
      /** 用原生 input 模拟 Element Plus Input 的 v-model。 */
      return () =>
        h('input', {
          ...attrs,
          placeholder: props.placeholder,
          value: props.modelValue,
          onInput: (event: Event) => emit('update:modelValue', (event.target as HTMLInputElement).value),
        });
    },
  }),
  ElOption: defineComponent({
    name: 'ElOption',
    props: {
      label: {
        type: String,
        required: true,
      },
      value: {
        type: String,
        required: true,
      },
    },
    setup(props) {
      return () => h('option', { value: props.value }, props.label);
    },
  }),
  ElSelect: defineComponent({
    name: 'ElSelect',
    props: {
      modelValue: {
        type: String,
        default: '',
      },
      placeholder: {
        type: String,
        default: '',
      },
    },
    emits: ['update:modelValue'],
    setup(props, { attrs, emit, slots }) {
      /** 用原生 select 模拟 Element Plus Select 的 v-model。 */
      return () =>
        h(
          'select',
          {
            ...attrs,
            value: props.modelValue,
            'aria-label': props.placeholder,
            onChange: (event: Event) => emit('update:modelValue', (event.target as HTMLSelectElement).value),
          },
          slots.default?.(),
        );
    },
  }),
  ElTable: defineComponent({
    name: 'ElTable',
    props: {
      data: {
        type: Array as PropType<unknown[]>,
        default: () => [],
      },
    },
    setup(props, { attrs, slots }) {
      /** 通过 provide 将表格行传给子列 stub，保留 row slot 测试能力。 */
      const rows = computed(() => props.data);
      provide(tableRowsKey, rows);
      return () => h('div', { ...attrs, class: ['el-table-stub', attrs.class] }, slots.default?.());
    },
  }),
  ElTableColumn: defineComponent({
    name: 'ElTableColumn',
    props: {
      label: {
        type: String,
        default: '',
      },
      prop: {
        type: String,
        default: '',
      },
    },
    setup(props, { slots }) {
      /** 渲染表头和每行单元格内容，支持默认 slot 或 prop 字段读取。 */
      const rows = inject<ComputedRef<Record<string, unknown>[]>>(tableRowsKey, computed(() => []));
      return () =>
        h('div', { class: 'el-table-column-stub' }, [
          props.label ? h('strong', props.label) : null,
          ...rows.value.map((row) =>
            h('div', { class: 'el-table-cell-stub' }, slots.default ? slots.default({ row }) : String(row[props.prop] ?? '')),
          ),
        ]);
    },
  }),
};
