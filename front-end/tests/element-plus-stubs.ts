import { computed, defineComponent, h, inject, provide, type ComputedRef, type PropType } from 'vue';

const tableRowsKey = Symbol('tableRows');

export const elementPlusStubs = {
  ElButton: defineComponent({
    name: 'ElButton',
    emits: ['click'],
    setup(_, { attrs, emit, slots }) {
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
      return () =>
        props.modelValue
          ? h('section', { class: 'el-dialog-stub' }, [h('h2', props.title), slots.default?.()])
          : null;
    },
  }),
  ElDropdown: defineComponent({
    name: 'ElDropdown',
    setup(_, { slots }) {
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
