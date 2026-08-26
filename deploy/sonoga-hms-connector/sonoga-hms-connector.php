<?php
/**
 * Plugin Name: Sonoga HMS Connector
 * Description: Synchronizes confirmed MotoPress Hotel Booking reservations with the Sonoga Django HMS.
 * Version: 0.1.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/*
 * HMS HTTP helper.
 */
function sonoga_hms_signed_post($path, array $payload) {

    $base_url = defined('SONOGA_HMS_BASE_URL')
        ? rtrim(SONOGA_HMS_BASE_URL, '/')
        : 'https://manage.sonogahotels.com';

    $secret = defined('SONOGA_HMS_WEBHOOK_SECRET')
        ? SONOGA_HMS_WEBHOOK_SECRET
        : '';

    if (!$secret) {
        return new WP_Error(
            'sonoga_missing_secret',
            'Sonoga HMS webhook secret is not configured.'
        );
    }

    $body      = wp_json_encode($payload);
    $timestamp = (string) time();

    $signature = hash_hmac(
        'sha256',
        $timestamp . '.' . $body,
        $secret
    );

    return wp_remote_post(
        $base_url . $path,
        [
            'timeout' => 20,
            'headers' => [
                'Content-Type'       => 'application/json',
                'X-Sonoga-Api-Key'   => $secret,
                'X-Sonoga-Timestamp' => $timestamp,
                'X-Sonoga-Signature' => 'sha256=' . $signature,
            ],
            'body' => $body,
        ]
    );
}


function sonoga_hms_ping() {
    return sonoga_hms_signed_post(
        '/api/wordpress/ping/',
        ['ping' => true]
    );
}


/*
 * MotoPress Accommodation Type ID -> Sonoga HMS RoomType code.
 */
function sonoga_hms_room_type_map() {

    return [
        1454 => 'FAM', // Family Suite
        1482 => 'STD', // Standard Room
        1478 => 'STE', // Executive Suite
    ];
}


/*
 * Resolve a MotoPress Booking object regardless of the exact
 * object/ID supplied by a MotoPress action.
 */
function sonoga_hms_resolve_booking(array $args) {

    foreach ($args as $arg) {

        if (
            is_object($arg) &&
            method_exists($arg, 'getReservedRooms') &&
            method_exists($arg, 'getId')
        ) {
            return $arg;
        }
    }

    if (!function_exists('mphb_get_booking')) {
        return null;
    }

    foreach ($args as $arg) {

        if (is_numeric($arg)) {

            $booking = mphb_get_booking((int) $arg);

            if ($booking) {
                return $booking;
            }
        }

        if (
            is_object($arg) &&
            method_exists($arg, 'getBookingId')
        ) {

            $booking_id = (int) $arg->getBookingId();

            if ($booking_id) {

                $booking = mphb_get_booking($booking_id);

                if ($booking) {
                    return $booking;
                }
            }
        }
    }

    return null;
}


/*
 * Convert one MotoPress booking into one HMS payload
 * per reserved room.
 *
 * Example:
 *
 * MPHB-1234-RR-5678
 */
function sonoga_hms_build_booking_payloads($booking, $status = 'CONFIRMED') {

    $map = sonoga_hms_room_type_map();

    $booking_id = (int) $booking->getId();

    $check_in  = $booking->getCheckInDate();
    $check_out = $booking->getCheckOutDate();

    $customer = $booking->getCustomer();

    $reserved_rooms = $booking->getReservedRooms();

    $nights = max(
        1,
        (int) $check_in->diff($check_out)->days
    );

    $payloads = [];

    foreach ($reserved_rooms as $reserved_room) {

        $room_type_id = (int) $reserved_room->getRoomTypeId();

        if (!isset($map[$room_type_id])) {

            error_log(
                'Sonoga HMS: unmapped MotoPress room type ID ' .
                $room_type_id .
                ' on booking ' .
                $booking_id
            );

            continue;
        }

        $reserved_room_id = (int) $reserved_room->getId();

        $room_total = (float) $reserved_room->calcRoomPrice(
            $check_in,
            $check_out
        );

        $nightly_rate = $room_total / $nights;

        $payloads[] = [

            'external_reference' =>
                'MPHB-' .
                $booking_id .
                '-RR-' .
                $reserved_room_id,

            'business_unit_code' => 'HOTEL',

            'room_type_code' => $map[$room_type_id],

            'arrival_date' =>
                $check_in->format('Y-m-d'),

            'departure_date' =>
                $check_out->format('Y-m-d'),

            'adults' =>
                (int) $reserved_room->getAdults(),

            'children' =>
                (int) $reserved_room->getChildren(),

            'nightly_rate' =>
                number_format(
                    $nightly_rate,
                    2,
                    '.',
                    ''
                ),

            'discount_amount' => '0.00',

            'tax_amount' => '0.00',

            'status' => $status,

            'special_requests' =>
                method_exists($booking, 'getNote')
                    ? (string) $booking->getNote()
                    : '',

            'guest' => [

                'first_name' =>
                    $customer
                        ? (string) $customer->getFirstName()
                        : '',

                'last_name' =>
                    $customer
                        ? (string) $customer->getLastName()
                        : '',

                'phone' =>
                    $customer
                        ? (string) $customer->getPhone()
                        : '',

                'email' =>
                    $customer
                        ? (string) $customer->getEmail()
                        : '',
            ],
        ];
    }

    return $payloads;
}


/*
 * Send all reserved rooms belonging to one MotoPress booking.
 */
function sonoga_hms_sync_booking($booking, $status = 'CONFIRMED') {

    $payloads = sonoga_hms_build_booking_payloads(
        $booking,
        $status
    );

    foreach ($payloads as $payload) {

        $response = sonoga_hms_signed_post(
            '/api/wordpress/bookings/',
            $payload
        );

        if (is_wp_error($response)) {

            error_log(
                'Sonoga HMS sync error: ' .
                $response->get_error_message()
            );

            continue;
        }

        $code = wp_remote_retrieve_response_code(
            $response
        );

        if ($code < 200 || $code >= 300) {

            error_log(
                'Sonoga HMS returned HTTP ' .
                $code .
                ' for ' .
                $payload['external_reference']
            );
        }
    }
}


/*
 * MotoPress confirmed-paid booking.
 */
function sonoga_hms_mphb_confirmed_with_payment(...$args) {

    $booking = sonoga_hms_resolve_booking($args);

    if (!$booking) {

        error_log(
            'Sonoga HMS: unable to resolve MotoPress booking.'
        );

        return;
    }

    sonoga_hms_sync_booking(
        $booking,
        'CONFIRMED'
    );
}


/*
 * MotoPress cancellation.
 */
function sonoga_hms_mphb_cancelled(...$args) {

    $booking = sonoga_hms_resolve_booking($args);

    if (!$booking) {
        return;
    }

    sonoga_hms_sync_booking(
        $booking,
        'CANCELLED'
    );
}


/*
 * IMPORTANT:
 *
 * Automatic synchronization stays disabled until
 * manage.sonogahotels.com passes the authenticated ping.
 */
if (
    defined('SONOGA_HMS_ENABLE_SYNC') &&
    SONOGA_HMS_ENABLE_SYNC
) {

    add_action(
        'mphb_booking_confirmed_with_payment',
        'sonoga_hms_mphb_confirmed_with_payment',
        20,
        10
    );

    add_action(
        'mphb_booking_cancelled',
        'sonoga_hms_mphb_cancelled',
        20,
        10
    );
}
