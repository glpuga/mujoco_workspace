#include <mujoco_viewer/viewer.h>

#include <cstdio>

#include <GLFW/glfw3.h>
#include <mujoco/mujoco.h>

namespace mujoco_viewer {
namespace {

// Everything the GLFW callbacks need, reached through the window user pointer.
struct ViewerState {
  mjModel* model = nullptr;
  mjData* data = nullptr;

  mjvCamera cam;
  mjvOption opt;
  mjvPerturb pert;
  mjvScene scene;
  mjrContext context;

  bool button_left = false;
  bool button_middle = false;
  bool button_right = false;
  double last_x = 0.0;
  double last_y = 0.0;

  bool paused = false;
  bool ui_pressed = false;
};

ViewerState* GetState(GLFWwindow* window) {
  return static_cast<ViewerState*>(glfwGetWindowUserPointer(window));
}

// On-screen control buttons, laid out in framebuffer pixels (bottom-left origin).
constexpr int kButtonWidth = 84;
constexpr int kButtonHeight = 30;
constexpr int kButtonGap = 8;
constexpr int kButtonMargin = 10;

void ComputeButtons(const mjrRect& viewport, mjrRect buttons[3]) {
  const int bottom = viewport.bottom + viewport.height - kButtonMargin - kButtonHeight;
  for (int i = 0; i < 3; ++i) {
    buttons[i].left = viewport.left + kButtonMargin + i * (kButtonWidth + kButtonGap);
    buttons[i].bottom = bottom;
    buttons[i].width = kButtonWidth;
    buttons[i].height = kButtonHeight;
  }
}

// Return the index of the button under (x, y) in framebuffer pixels, or -1.
int HitTestButton(const mjrRect& viewport, double x, double y) {
  mjrRect buttons[3];
  ComputeButtons(viewport, buttons);
  for (int i = 0; i < 3; ++i) {
    if (x >= buttons[i].left && x < buttons[i].left + buttons[i].width && y >= buttons[i].bottom &&
        y < buttons[i].bottom + buttons[i].height) {
      return i;
    }
  }
  return -1;
}

void ApplyButton(ViewerState* state, int index) {
  switch (index) {
    case 0:  // Pause
      state->paused = true;
      break;
    case 1:  // Reset
      mj_resetData(state->model, state->data);
      mj_forward(state->model, state->data);
      mju_zero(state->data->xfrc_applied, 6 * state->model->nbody);
      break;
    case 2:  // Play
      state->paused = false;
      break;
  }
}

void DrawButtons(const ViewerState& state, const mjrRect& viewport) {
  const char* labels[3] = {"Pause", "Reset", "Play"};
  mjrRect buttons[3];
  ComputeButtons(viewport, buttons);
  for (int i = 0; i < 3; ++i) {
    // Highlight whichever of Pause/Play reflects the current run state.
    const bool highlighted = (i == 0 && state.paused) || (i == 2 && !state.paused);
    if (highlighted) {
      mjr_rectangle(buttons[i], 0.15f, 0.45f, 0.85f, 0.9f);
    } else {
      mjr_rectangle(buttons[i], 0.20f, 0.20f, 0.25f, 0.85f);
    }
    // mjGRID_TOP draws the label horizontally centred at the top of the button.
    mjr_overlay(mjFONT_NORMAL, mjGRID_TOP, buttons[i], labels[i], nullptr, &state.context);
  }

  if (state.paused) {
    mjr_overlay(mjFONT_BIG, mjGRID_TOP, viewport, "PAUSED", nullptr, &state.context);
  }
}

// Backspace resets the simulation to its initial state.
void OnKey(GLFWwindow* window, int key, int /*scancode*/, int action, int /*mods*/) {
  if (action == GLFW_PRESS && key == GLFW_KEY_BACKSPACE) {
    ViewerState* state = GetState(window);
    mj_resetData(state->model, state->data);
    mj_forward(state->model, state->data);
  }
}

// Find the dynamic body under the cursor and record it as the perturbation
// target, storing the click point in the body's local frame.
void SelectUnderCursor(GLFWwindow* window, ViewerState* state) {
  double xpos = 0.0;
  double ypos = 0.0;
  glfwGetCursorPos(window, &xpos, &ypos);

  int width = 0;
  int height = 0;
  glfwGetWindowSize(window, &width, &height);
  if (width <= 0 || height <= 0) {
    return;
  }

  // mjv_select expects a bottom-left origin and the viewport aspect ratio.
  const mjtNum aspect = static_cast<mjtNum>(width) / height;
  const mjtNum rel_x = static_cast<mjtNum>(xpos / width);
  const mjtNum rel_y = static_cast<mjtNum>(1.0 - ypos / height);

  mjtNum selpnt[3] = {0, 0, 0};
  int geom_id = -1;
  int flex_id = -1;
  int skin_id = -1;
  const int body = mjv_select(
      state->model, state->data, &state->opt, aspect, rel_x, rel_y, &state->scene, selpnt, &geom_id, &flex_id,
      &skin_id);

  if (body <= 0) {  // 0 is the world body; nothing dynamic was hit
    state->pert.select = 0;
    state->pert.flexselect = -1;
    state->pert.skinselect = -1;
    return;
  }

  state->pert.select = body;
  state->pert.flexselect = flex_id;
  state->pert.skinselect = skin_id;

  // Selection point in the body frame, so the force acts where the user clicked.
  mjtNum offset[3];
  mju_sub3(offset, selpnt, state->data->xpos + 3 * body);
  mju_mulMatTVec(state->pert.localpos, state->data->xmat + 9 * body, offset, 3, 3);
}

void OnMouseButton(GLFWwindow* window, int button, int action, int mods) {
  ViewerState* state = GetState(window);

  // Track buttons from the event itself; glfwGetMouseButton can lag on some
  // platforms, which would make the drag action fall back to zoom.
  if (button == GLFW_MOUSE_BUTTON_LEFT) {
    state->button_left = (action == GLFW_PRESS);
  } else if (button == GLFW_MOUSE_BUTTON_MIDDLE) {
    state->button_middle = (action == GLFW_PRESS);
  } else if (button == GLFW_MOUSE_BUTTON_RIGHT) {
    state->button_right = (action == GLFW_PRESS);
  }
  glfwGetCursorPos(window, &state->last_x, &state->last_y);

  // On-screen control buttons take priority over camera/perturbation drags.
  if (action == GLFW_PRESS && button == GLFW_MOUSE_BUTTON_LEFT) {
    int fb_width = 0;
    int fb_height = 0;
    int win_width = 0;
    int win_height = 0;
    glfwGetFramebufferSize(window, &fb_width, &fb_height);
    glfwGetWindowSize(window, &win_width, &win_height);
    if (win_width > 0 && win_height > 0) {
      const double fb_x = state->last_x * fb_width / win_width;
      const double fb_y = (win_height - state->last_y) * fb_height / win_height;
      const mjrRect viewport = {0, 0, fb_width, fb_height};
      const int hit = HitTestButton(viewport, fb_x, fb_y);
      if (hit >= 0) {
        ApplyButton(state, hit);
        state->button_left = false;  // swallow the press so no camera drag starts
        state->ui_pressed = true;
        return;
      }
    }
  }
  if (action == GLFW_RELEASE) {
    state->ui_pressed = false;
  }

  const bool control = (mods & GLFW_MOD_CONTROL) != 0 || glfwGetKey(window, GLFW_KEY_LEFT_CONTROL) == GLFW_PRESS ||
                       glfwGetKey(window, GLFW_KEY_RIGHT_CONTROL) == GLFW_PRESS;

  // Ctrl + drag pushes the body under the cursor instead of moving the camera:
  // left button rotates it, right button translates it.
  if (action == GLFW_PRESS && control && (button == GLFW_MOUSE_BUTTON_LEFT || button == GLFW_MOUSE_BUTTON_RIGHT)) {
    SelectUnderCursor(window, state);
    if (state->pert.select > 0) {
      mjv_initPerturb(state->model, state->data, &state->scene, &state->pert);
      // mjv_initPerturb derives the translation scale from the current camera;
      // fall back to the model extent if it comes out degenerate so dragging
      // can still move the body.
      if (!(state->pert.scale > 0.0)) {
        state->pert.scale = state->model->stat.extent;
      }
      state->pert.active = (button == GLFW_MOUSE_BUTTON_RIGHT) ? mjPERT_TRANSLATE : mjPERT_ROTATE;
    } else {
      state->pert.active = 0;
    }
  } else if (action == GLFW_RELEASE && state->pert.active) {
    state->pert.active = 0;
    if (state->pert.select > 0) {
      mju_zero(state->data->xfrc_applied + 6 * state->pert.select, 6);
    }
  }
}

void OnMouseMove(GLFWwindow* window, double xpos, double ypos) {
  ViewerState* state = GetState(window);
  if (state->ui_pressed) {
    return;
  }
  if (!state->pert.active && !state->button_left && !state->button_middle && !state->button_right) {
    return;
  }

  const double dx = xpos - state->last_x;
  const double dy = ypos - state->last_y;
  state->last_x = xpos;
  state->last_y = ypos;

  int width = 0;
  int height = 0;
  glfwGetWindowSize(window, &width, &height);
  if (height == 0) {
    return;
  }
  (void)width;  // Only the height is used to normalise the mouse delta.

  const bool shift =
      glfwGetKey(window, GLFW_KEY_LEFT_SHIFT) == GLFW_PRESS || glfwGetKey(window, GLFW_KEY_RIGHT_SHIFT) == GLFW_PRESS;

  // While perturbing, the motion mode is fixed by pert.active: translate moves
  // the selection point in a plane, rotate spins the body around it. The camera
  // move instead follows which button is held.
  if (state->pert.active) {
    const mjtMouse action = (state->pert.active == mjPERT_TRANSLATE) ? (shift ? mjMOUSE_MOVE_H : mjMOUSE_MOVE_V)
                                                                     : (shift ? mjMOUSE_ROTATE_H : mjMOUSE_ROTATE_V);
    mjv_movePerturb(state->model, state->data, action, dx / height, dy / height, &state->scene, &state->pert);
  } else {
    mjtMouse action;
    if (state->button_right) {
      action = shift ? mjMOUSE_MOVE_H : mjMOUSE_MOVE_V;
    } else if (state->button_left) {
      action = shift ? mjMOUSE_ROTATE_H : mjMOUSE_ROTATE_V;
    } else {
      action = mjMOUSE_ZOOM;
    }
    mjv_moveCamera(state->model, action, dx / height, dy / height, &state->cam);
  }
}

void OnScroll(GLFWwindow* window, double /*xoffset*/, double yoffset) {
  ViewerState* state = GetState(window);
  mjv_moveCamera(state->model, mjMOUSE_ZOOM, 0, -0.05 * yoffset, &state->cam);
}

}  // namespace

bool Launch(mjModel* model, mjData* data, const Options& options) {
  if (glfwInit() == 0) {
    std::fprintf(stderr, "mujoco_viewer: could not initialize GLFW\n");
    return false;
  }

  GLFWwindow* window = glfwCreateWindow(options.width, options.height, options.title.c_str(), nullptr, nullptr);
  if (window == nullptr) {
    std::fprintf(stderr, "mujoco_viewer: could not create window (is a display available?)\n");
    return false;
  }
  glfwMakeContextCurrent(window);
  glfwSwapInterval(1);

  // Initialise the visualisation structures, then allocate the scene and the
  // OpenGL render context. Every early return above happens before this point,
  // so a single teardown block at the end is enough.
  ViewerState state;
  state.model = model;
  state.data = data;
  mjv_defaultCamera(&state.cam);
  mjv_defaultOption(&state.opt);
  mjv_defaultPerturb(&state.pert);
  state.opt.flags[mjVIS_PERTFORCE] = 1;  // draw the force arrow while perturbing
  mjv_defaultScene(&state.scene);
  mjr_defaultContext(&state.context);
  mjv_makeScene(model, &state.scene, options.max_geoms);
  mjr_makeContext(model, &state.context, mjFONTSCALE_150);

  glfwSetWindowUserPointer(window, &state);
  glfwSetKeyCallback(window, OnKey);
  glfwSetCursorPosCallback(window, OnMouseMove);
  glfwSetMouseButtonCallback(window, OnMouseButton);
  glfwSetScrollCallback(window, OnScroll);

  while (glfwWindowShouldClose(window) == 0) {
    // Turn an active mouse perturbation into an external force on the selected
    // body. Reset just that body's applied force each frame so the push does not
    // accumulate and any other forces the caller set are left untouched.
    if (!state.paused && state.pert.active && state.pert.select > 0) {
      mju_zero(data->xfrc_applied + 6 * state.pert.select, 6);
      mjv_applyPerturbPose(model, data, &state.pert, 0);
      mjv_applyPerturbForce(model, data, &state.pert);
    }

    if (state.paused) {
      // Frozen: refresh derived quantities so the scene still renders correctly
      // (and reflects a reset) without advancing time.
      mj_forward(model, data);
    } else {
      // Advance physics towards real time: step until one frame worth of
      // simulated time has elapsed. On a model that is faster than wall-clock
      // this keeps the window running at roughly the requested frame interval.
      const mjtNum frame_start = data->time;
      while (data->time - frame_start < options.frame_interval) {
        mj_step(model, data);
      }
    }

    mjrRect viewport = {0, 0, 0, 0};
    glfwGetFramebufferSize(window, &viewport.width, &viewport.height);
    mjv_updateScene(model, data, &state.opt, &state.pert, &state.cam, mjCAT_ALL, &state.scene);
    mjr_render(viewport, &state.scene, &state.context);
    DrawButtons(state, viewport);
    glfwSwapBuffers(window);
    glfwPollEvents();
  }

  mjv_freeScene(&state.scene);
  mjr_freeContext(&state.context);
  glfwDestroyWindow(window);
  return true;
}

}  // namespace mujoco_viewer
