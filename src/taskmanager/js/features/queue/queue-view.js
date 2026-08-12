import { emptyState, icon, pageHeader, projectStatusText, statusBadge } from '../../ui/components.js';
import { renderMarkdown } from '../../ui/markdown.js';
import { aggregateDomain, getQueueCustomOrdering, getState, queueCustomOrderKey } from '../../state/store.js';
import { escapeHtml, formatRelativeTime, normalizePath, slugify } from '../../lib/utils.js';
import {
  absoluteTaskPath,
  actionLink,
  answeredQuestionCount,
  button,
  checklistSummary,
  cleanStatusLabel,
  createdLabel,
  fileLabel,
  lifecycleValueForTask,
  modifiedLabel,
  plural,
  queueScopeLabel,
  queueStatusFilterValue,
  renderChecklistAccordion,
  renderAgentActivityPanel,
  renderPlanMetadataPanels,
  renderPriorityCommentPanel,
  riskLabel,
  routeWithSavedSort,
  scoreCaption,
  scoreRingHtml,
  selectedTask,
  sortHeader,
  sortTasks,
  sortTasksByCustomOrder,
  statusFilterTabs,
  stripPlanDocumentChrome,
  taskCompletionGate,
  taskMatchesQueueFilters,
  taskRecentChanges,
  taskStatusControl,
  taskStatusStateClass,
} from '../../ui/view-helpers.js';

function renderLedgerRow(task, selected, options = {}) {
  const { customOrderEnabled = false, customOrderIndex = 0 } = options;
  const status = cleanStatusLabel(task.status);
  const recentChanges = taskRecentChanges(task);
  const selectedClass = task.id === selected?.id ? 'active' : '';
  const updatedClass = recentChanges.length ? 'recently-updated' : '';
  const statusStateClass = taskStatusStateClass(task);
  const questionsLabel = task.unansweredQuestions ? `${task.unansweredQuestions} open` : task.questionCount ? `${answeredQuestionCount(task)} / ${task.questionCount}` : 'Ready';
  const taskHref = task.source === 'plan' ? `#/task?id=${encodeURIComponent(task.id)}` : '#/';
  const questionHref = `#/questions?task=${encodeURIComponent(task.id)}`;
  const questionsDisabled = ['in-progress', 'review', 'user-verification', 'failed-user-verification', 'completed', 'archive'].includes(task.lifecycle) || !task.questionCount;
  const checklist = checklistSummary(task);
  const questionAction = questionsDisabled
    ? `<span class="btn btn-mini btn-disabled" aria-disabled="true" title="Questions are not available from this queue row">View questions</span>`
    : `<a class="btn btn-mini" href="${questionHref}">View questions</a>`;
  const statusControl = taskStatusControl(task);
  const block = task.block || task.manifest?.block || {};
  const operationalBadges = [
    block?.blocked ? '<span class="badge badge-warning">Blocked metadata</span>' : '',
    task.automation?.claimed || task.manifest?.automation?.claimed ? '<span class="badge">Automation claimed</span>' : '',
  ].filter(Boolean).join('');
  const orderKey = queueCustomOrderKey(task);
  const dragHandle = customOrderEnabled ? `<button class="queue-drag-handle" type="button" title="Drag to set run order" aria-label="Drag ${escapeHtml(task.title)} to set run order"><span>${escapeHtml(String(customOrderIndex).padStart(2, '0'))}</span><i aria-hidden="true">⋮⋮</i></button>` : '';
  return `<div class="ledger-row-shell ${statusStateClass} ${selectedClass} ${updatedClass} ${customOrderEnabled ? 'custom-order-enabled' : ''}" data-filter-row ${customOrderEnabled ? `data-custom-order-key="${escapeHtml(orderKey)}" data-custom-order-index="${customOrderIndex}" draggable="true"` : ''}>${dragHandle}
      <div class="ledger-row" role="button" tabindex="0" data-action="select-queue-task" data-task-id="${escapeHtml(task.id)}" aria-label="Open ${escapeHtml(task.title)}">
        <span class="ledger-identity"><span class="ledger-icon">${icon('tasks')}</span><span class="ledger-copy"><strong>${escapeHtml(task.title)}</strong><span>${escapeHtml(task.description || task.path || 'No description recorded.')}</span>${operationalBadges ? `<span class="inline-actions">${operationalBadges}</span>` : ''}</span></span>
        <span class="ledger-cell ledger-project"><strong>${escapeHtml(task.projectName)}</strong><span>Project</span></span>
        <span class="ledger-cell ledger-status">${statusControl}</span>
        <span class="ledger-cell ledger-created"><strong>${escapeHtml(createdLabel(task))}</strong><span>Created</span></span>
        <span class="ledger-cell ledger-modified"><strong>${escapeHtml(modifiedLabel(task))}</strong><span>Modified</span></span>
        <span class="ledger-cell ledger-questions"><strong>${escapeHtml(questionsLabel)}</strong><span>Questions</span></span>
        <span class="ledger-cell ledger-progress"><strong>${escapeHtml(checklist.label)}</strong><span>Checks</span>${checklist.total ? `<span class="mini-progress" aria-hidden="true"><i style="width:${checklist.percent}%"></i></span>` : ''}</span>
      </div>
      <div class="ledger-row-actions"><a class="btn btn-mini btn-primary" href="${taskHref}">View task</a>${questionAction}</div>
    </div>`;
}

function renderQueueGroup(label, tasks, selected) {
  if (!tasks.length) return '';
  return `<section class="queue-group"><div class="queue-group-label"><span>${escapeHtml(label)}</span><span>${tasks.length}</span></div>${tasks.map((task) => renderLedgerRow(task, selected)).join('')}</section>`;
}

function renderSidebarAccordion({ title, eyebrow = '', body = '', className = '', open = false, attrs = '' }) {
  return `<section class="sidebar-accordion-block ${className}" ${attrs}>
    <details class="sidebar-accordion" ${open ? 'open' : ''}>
      <summary>${eyebrow ? `<span>${escapeHtml(eyebrow)}</span>` : ''}<strong>${escapeHtml(title)}</strong></summary>
      <div class="sidebar-accordion-body">${body}</div>
    </details>
  </section>`;
}

export function renderUserFeedbackPanel(task) {
  if (task?.source !== 'plan') return '';
  const status = cleanStatusLabel(task.status);
  if (task.lifecycle === 'user-verification') {
    if (/sent to agent/i.test(status)) {
      return renderSidebarAccordion({
        title: 'Comment sent to agent',
        className: 'user-feedback-saved user-verification-comment-sent',
        open: false,
        body: `<p>Your comment has been written into the plan. Current status: <span class="status-text">Sent to Agent</span>.</p>`,
      });
    }
    const completionGate = taskCompletionGate(task);
    const confirmAttrs = `data-task-id="${escapeHtml(task.id)}" ${completionGate.allowed ? '' : `disabled aria-disabled="true" title="${escapeHtml(completionGate.reason)}"`}`;
    const confirmHelp = completionGate.allowed
      ? 'This confirms the work is functioning and moves the plan to completed while removing the active todo entry.'
      : `Confirm Working is locked: ${completionGate.reason}.`;
    return renderSidebarAccordion({
      title: 'Confirm or comment',
      eyebrow: 'User verification',
      className: 'user-verification-comment-panel',
      attrs: 'data-user-verification-comment-panel',
      body: `<p>If the work is functioning, confirm it. If you need an explanation or follow-up, send a concise comment to the agent.</p><div class="inline-actions">${button('Confirm Working', 'confirm-user-verification', { primary: true, attrs: confirmAttrs })}</div><p class="feedback-help">${escapeHtml(confirmHelp)}</p><textarea class="textarea" rows="5" data-user-verification-comment-text data-draft-key="user-verification-comment:${escapeHtml(task.id)}" placeholder="Tell the agent what to explain or adjust…"></textarea><div class="inline-actions">${button('Send comment to agent', 'send-user-verification-comment', { attrs: `data-task-id="${escapeHtml(task.id)}"` })}</div>`,
    });
  }
  if (task.lifecycle !== 'failed-user-verification') return '';
  if (/user replied/i.test(status)) {
    return renderSidebarAccordion({
      title: 'User feedback',
      className: 'user-feedback-saved',
      open: false,
      body: `<p>The feedback has been saved into the plan. Current status: <span class="status-text">User Replied</span>.</p>`,
    });
  }
  return renderSidebarAccordion({
    title: 'User feedback required',
    className: 'user-feedback-panel',
    attrs: 'data-user-feedback-panel',
    body: `<p>Describe what is not fixed, not implemented, or still needs to change. Saving writes the feedback into the plan and sets the task status to <strong>User Replied</strong>.</p><textarea class="textarea" rows="5" data-user-feedback-text data-draft-key="user-feedback:${escapeHtml(task.id)}" placeholder="Example: The badge displays correctly in canvas, but preview still has the wrong spacing on mobile."></textarea><div class="inline-actions">${button('Save user feedback', 'save-user-feedback', { primary: true, attrs: `data-task-id="${escapeHtml(task.id)}"` })}</div>`,
  });
}

function renderInspectorSource(task, fullPlanPath) {
  const copyAction = fullPlanPath
    ? button('Copy path', 'copy-text', { iconName: 'copy', attrs: `data-copy-text="${escapeHtml(fullPlanPath)}" data-copy-toast="Plan path copied."` })
    : '';
  return `<section class="inspector-source-panel">
    <span>Source file</span>
    <code title="${escapeHtml(task.path || '')}">${escapeHtml(task.path || '')}</code>
    ${copyAction}
  </section>`;
}

export function renderQueue(route) {
  const state = getState();
  const domain = aggregateDomain();
  if (!state.projects.length) {
    return `<div class="workspace-page queue-workspace">
      <header class="workspace-toolbar"><div class="workspace-heading"><div class="workspace-heading-copy"><h1>Instruction queue</h1><p>Every instruction becomes a traceable task record before execution starts.</p></div></div><div class="header-actions">${button('Connect project', 'connect-project', { primary: true, iconName: 'plus' })}</div></header>
      <div class="workspace-empty">${emptyState({ title: 'Connect the first task system', description: 'Select a project directory containing a generated task workflow. TaskManager starts with no sample records.', action: button('Connect project folder', 'connect-project', { primary: true, iconName: 'projects' }), iconName: 'projects' })}</div>
    </div>`;
  }
  const statusFilter = route.params.get('status') || 'all';
  const effectiveRoute = routeWithSavedSort(route, 'queue', { sort: 'created', dir: 'asc' });
  const completedTasks = domain.tasks.filter((task) => queueStatusFilterValue(task) === 'completed');
  const statusTabTasks = [...domain.queue, ...completedTasks];
  const queueSource = statusFilter === 'completed' ? completedTasks : domain.queue;
  const filteredQueue = queueSource.filter((task) => taskMatchesQueueFilters(task, route));
  const projectScopedOrdering = state.selectedProjectId !== 'all';
  const customOrdering = getQueueCustomOrdering(state.selectedProjectId);
  const fallbackSortedQueue = sortTasks(filteredQueue, effectiveRoute);
  const customOrderEnabled = Boolean(projectScopedOrdering && customOrdering.enabled && statusFilter !== 'completed');
  const sortedQueue = customOrderEnabled ? sortTasksByCustomOrder(filteredQueue, fallbackSortedQueue, customOrdering.order) : fallbackSortedQueue;
  const activeOrderKeys = fallbackSortedQueue.map(queueCustomOrderKey);
  const selectedId = state.selectedQueueTaskId || sortedQueue[0]?.id;
  const selected = sortedQueue.find((task) => task.id === selectedId) || sortedQueue[0] || null;
  const allIncludedQueueCount = state.projects
    .filter((project) => project.includeInAllQueue !== false)
    .reduce((count, project) => count + (state.projectData.get(project.id)?.queue?.length || 0), 0);
  const visibleProjectCount = state.selectedProjectId === 'all' ? allIncludedQueueCount : (state.projectData.get(state.selectedProjectId)?.queue?.length || 0);
  const projectButtons = [
    `<div class="project-filter-shell"><button class="project-filter ${state.selectedProjectId === 'all' ? 'active' : ''}" type="button" data-action="select-project" data-project-id="all"><span class="project-dot"></span><span class="project-filter-copy"><strong>All projects</strong><span>Included project plans only</span></span><span class="project-filter-count">${String(allIncludedQueueCount).padStart(2, '0')}</span></button></div>`,
    ...state.projects.map((project) => {
      const data = state.projectData.get(project.id);
      const count = data?.queue?.length || 0;
      const included = project.includeInAllQueue !== false;
      const toggleLabel = included ? `Exclude ${project.name} from All projects` : `Include ${project.name} in All projects`;
      return `<div class="project-filter-shell"><button class="project-filter ${state.selectedProjectId === project.id ? 'active' : ''}" type="button" data-action="select-project" data-project-id="${escapeHtml(project.id)}"><span class="project-dot"></span><span class="project-filter-copy"><strong>${escapeHtml(project.name)}</strong><span>${count} open record${count === 1 ? '' : 's'}${included ? '' : ' · hidden from All'}</span></span><span class="project-filter-count">${String(count).padStart(2, '0')}</span></button><button class="project-all-toggle ${included ? 'included' : ''}" type="button" data-action="toggle-project-all-inclusion" data-project-id="${escapeHtml(project.id)}" aria-pressed="${included}" aria-label="${escapeHtml(toggleLabel)}" title="${escapeHtml(toggleLabel)}"></button></div>`;
    }),
  ].join('');
  const statusTabs = statusFilterTabs(statusTabTasks, route, statusFilter, domain.queue.length);
  const customOrderUnavailable = statusFilter === 'completed' || !projectScopedOrdering;
  const customOrderCopy = customOrderEnabled
    ? `Drag rows to set the run sequence for ${queueScopeLabel(state)}. Top row runs first.`
    : statusFilter === 'completed'
      ? 'Completed rows are no longer part of the active custom run order.'
      : !projectScopedOrdering
        ? 'Select a specific project to enable and edit custom run order. All projects always uses timestamp sorting.'
        : `Use saved timestamp sorting, or enable manual run order for ${queueScopeLabel(state)}.`;
  const orderToggle = `<div class="queue-order-toolbar"><div class="queue-order-copy"><strong>${customOrderEnabled ? 'Custom run order active' : 'Project custom run order'}</strong><span>${escapeHtml(customOrderCopy)}</span></div><button class="custom-order-toggle ${customOrdering.enabled ? 'active' : ''}" type="button" data-action="toggle-custom-queue-order" aria-pressed="${customOrdering.enabled}" ${customOrderUnavailable ? 'disabled' : ''}><span class="toggle-dot"></span><span>${customOrdering.enabled ? 'Enabled' : 'Enable'}</span></button></div>`;
  const ledger = queueSource.length
    ? (sortedQueue.length
      ? sortedQueue.map((task, index) => renderLedgerRow(task, selected, { customOrderEnabled, customOrderIndex: index + 1 })).join('')
      : emptyState({ title: 'No queue records match this status', description: 'Change the status filter to show more records.', iconName: 'filter' }))
    : emptyState({ title: statusFilter === 'completed' ? 'No completed instructions' : 'No open instructions', description: statusFilter === 'completed' ? 'Completed tasks will appear here after they are closed.' : 'Connected task systems contain no active task records.', iconName: statusFilter === 'completed' ? 'check' : 'check' });
  return `<div class="workspace-page queue-workspace">
    <header class="workspace-toolbar"><div class="workspace-heading"><div class="workspace-heading-copy"><h1>Instruction queue</h1><p>Every instruction becomes a traceable task record before execution starts.</p></div></div><div class="header-actions">${button('Capture instruction', 'open-capture', { primary: true, iconName: 'plus' })}</div></header>
    <div class="workspace-body">
      <aside class="workspace-pane project-rail" aria-label="Project filters"><div class="pane-header"><strong>Project scope</strong><span>${visibleProjectCount} open records</span></div><div class="project-filter-list">${projectButtons}</div></aside>
      <section class="workspace-pane queue-pane" aria-label="Instruction ledger"><div class="queue-toolbar"><div class="input-wrap">${icon('search')}<input class="input" type="search" placeholder="Search captured instructions…" aria-label="Search captured instructions" data-live-filter=".ledger-row-shell"></div><div class="inline-actions">${statusBadge(`Watching ${plural(state.projects.length, 'folder')}`)}</div></div>${statusTabs}${orderToggle}<div class="queue-column-head ${customOrderEnabled ? 'custom-order-mode' : ''}">${customOrderEnabled ? '<span>Order</span>' : ''}<span>Instruction</span><span>Project</span><span>Status</span>${sortHeader(effectiveRoute, '/', 'created', 'Created')}${sortHeader(effectiveRoute, '/', 'modified', 'Modified')}<span>Questions</span><span>Progress</span><span>Actions</span></div><div class="queue-row-list" data-custom-order-active-keys="${escapeHtml(activeOrderKeys.join('|'))}">${ledger}</div></section>
      <aside class="workspace-pane inspector-pane queue-inspector" data-queue-inspector>${selected ? renderQueueInspector(selected) : emptyState({ title: 'Nothing selected', description: 'Select an instruction from the ledger.', iconName: 'queue' })}</aside>
    </div>
  </div>`;
}

function renderQueueInspector(task) {
  const fullPlanPath = absoluteTaskPath(task);
  return `<div class="inspector-top"><strong>Capture inspector</strong><span>Selected instruction and lifecycle</span></div>
    ${renderAgentActivityPanel(task)}
    ${renderPriorityCommentPanel(task)}
    ${renderUserFeedbackPanel(task)}
    <div class="inspector-header"><span class="page-kicker">Captured instruction</span><h2>${escapeHtml(task.title)}</h2><p>${escapeHtml(task.description || 'No scope description recorded.')}</p></div>
    ${renderPlanMetadataPanels(task)}
    ${renderChecklistAccordion(task, 'Checklist in plan order')}
    ${renderInspectorSource(task, fullPlanPath)}
    <div class="inspector-actions">${task.source === 'plan' ? actionLink('Inspect full plan', '/task', { id: task.id }, true) : actionLink('Open queue', '/', {}, true)}${task.unansweredQuestions ? actionLink('Answer questions', '/questions', { task: task.id }) : ''}</div>`;
}
