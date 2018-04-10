import tensorflow as tf
import se3
import math as m


# assumes time major
def se3_losses(outputs, labels, k):
    with tf.variable_scope("se3_losses"):
        diff_p = outputs[:, :, 0:3] - labels[:, :, 0:3]
        # diff_q = outputs[:, :, 3:] - labels[:, :, 3:]
        q_dot_squared = tf.square(tf.reduce_sum(tf.multiply(outputs[:, :, 3:], labels[:, :, 3:]), 2))
        diff_q = tf.subtract(tf.constant(1.0, dtype=tf.float32), q_dot_squared)

        # takes the the dot product and sum it up along time
        sum_diff_p_dot_p = tf.reduce_sum(tf.multiply(diff_p, diff_p), axis=(0, 2,))
        # sum_diff_q_dot_q = tf.reduce_sum(tf.multiply(diff_q, diff_q), axis=(0, 2,))
        sum_diff_q_dot_q = tf.reduce_sum(diff_q, 0)

        t = tf.cast(tf.shape(outputs)[0], tf.float32)

        # multiplies the sum by 1 / t
        loss = (sum_diff_p_dot_p + k * sum_diff_q_dot_q) / t

        return tf.reduce_mean(loss), tf.reduce_mean(sum_diff_p_dot_p / t), tf.reduce_mean(sum_diff_q_dot_q / t)


def pair_train_fc_losses(outputs, labels_u, k):
    with tf.variable_scope("pair_train_fc_losses"):
        diff_p = outputs[:, :, 0:3] - labels_u[:, :, 0:3]
        diff_e = outputs[:, :, 3:6] - labels_u[:, :, 3:6]

        too_big = tf.greater(diff_e, tf.constant(m.pi, dtype=tf.float32))
        too_small = tf.less(diff_e, tf.constant(-m.pi, dtype=tf.float32))

        wrapped_diff_e = tf.where(too_big, tf.subtract(diff_e, tf.constant(2 * m.pi, dtype=tf.float32)),
                                  tf.where(too_small, tf.add(diff_e, tf.constant(2 * m.pi, dtype=tf.float32)), diff_e))

        # takes the the dot product and sum it up along time
        diff_p_sq = tf.multiply(diff_p, diff_p)
        sum_diff_p_dot_p = tf.reduce_sum(diff_p_sq, axis=(0, 2,))
        # sum_diff_e_dot_e = tf.reduce_sum(tf.multiply(diff_e, diff_e), axis=(0, 2,))
        sum_diff_e_dot_e = tf.reduce_sum(tf.multiply(wrapped_diff_e, wrapped_diff_e), axis=(0, 2,))

        t = tf.cast(tf.shape(outputs)[0], tf.float32)

        # multiplies the sum by 1 / t
        loss = (sum_diff_p_dot_p + k * sum_diff_e_dot_e) / t

        # return xyz losses
        x_loss = tf.reduce_mean(diff_p_sq[:, :, 0])
        y_loss = tf.reduce_mean(diff_p_sq[:, :, 1])
        z_loss = tf.reduce_mean(diff_p_sq[:, :, 2])

        return tf.reduce_mean(loss), tf.reduce_mean(sum_diff_p_dot_p / t), tf.reduce_mean(sum_diff_e_dot_e / t), \
               x_loss, y_loss, z_loss


# reduce_prod for tensor length 6, x shape is [time length, batch size, 6]
def reduce_prod_6(x):
    r = tf.multiply(x[:, :, 0], x[:, :, 1])
    r = tf.multiply(r, x[:, :, 2])
    r = tf.multiply(r, x[:, :, 3])
    r = tf.multiply(r, x[:, :, 4])
    r = tf.multiply(r, x[:, :, 5])

    return r


# assumes time major
def fc_losses(outputs, labels_u):
    with tf.variable_scope("fc_losses"):
        diff_u = outputs[:, :, 0:6] - labels_u
        L = outputs[:, :, 6:12]

        # The network outputs Q=LL* through the Cholesky decomposition,
        # we assume L is diagonal, Q is always psd
        Q = tf.multiply(L, L)

        # determinant of a diagonal matrix is product of it diagonal
        # log_det_Q = tf.log(tf.reduce_prod(Q, axis=2) + 1e-8)
        log_det_Q = tf.log(reduce_prod_6(Q) + 1e-8)

        # inverse of a diagonal matrix is elemental inverse
        inv_Q = tf.div(tf.constant(1, dtype=tf.float32), Q + 1e-8)

        # sum of determinants along the time
        sum_det_Q = tf.reduce_sum(log_det_Q, axis=0)

        # sum of diff_u' * inv_Q * diff_u
        s = tf.reduce_sum(tf.multiply(diff_u, tf.multiply(inv_Q, diff_u)), axis=(0, 2,))

        t = tf.cast(tf.shape(outputs)[0], tf.float32)

        # add and multiplies of sum by 1 / t
        loss = (s + sum_det_Q) / t

        return tf.reduce_mean(loss)
